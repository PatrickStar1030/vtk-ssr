from wslink import server, register as exportRpc
from vtkmodules.web.wslink import ServerProtocol
from vtkmodules.web import protocols, wslink as vtk_wslink
import vtk
import argparse
import os
import time

class FPSCallback:
    def __init__(self, render_window, renderer):
        self.render_window = render_window
        self.renderer = renderer
        self.text_actor = vtk.vtkTextActor()        
        self.text_actor.GetTextProperty().SetFontSize(24)
        self.text_actor.GetTextProperty().SetColor(1, 1, 0)
        # 调整位置到右上角
        self.text_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.text_actor.SetPosition(0.85, 0.9)
        
        self.renderer.AddActor2D(self.text_actor)
        self.last_time = time.time()
        self.frame_count = 0

    def execute(self, obj, event):
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        if elapsed > 1.0:
            fps = self.frame_count / elapsed
            self.text_actor.SetInput(f"FPS: {fps:.1f}")
            self.last_time = current_time
            self.frame_count = 0
        self.render_window.Render()


# VR实现
# 1. 初始化渲染器
# 2. io数据解析
# 3. 离屏渲染+交互设置
# 4. 传输曲线选择
# 5. 调窗
class VRRender:
    def __init__(
        self,
        dicom_dir,
        render_window,
        renderer,
        interactor,
        window=2000,
        level=1000,
        colormap=None,  # colormap: list of (value, r, g, b) tuples or None
        opacity_map=None,  # opacity_map: list of (value, opacity) tuples or None
    ):
        if renderer is None or render_window is None or interactor is None:
            raise ValueError(
                "renderer, render_window, and interactor must all be provided and cannot be None"
            )
        self.dicom_dir = dicom_dir
        self.image_reader = None
        self.volume = None
        self.render_window = render_window
        self.renderer = renderer
        self.interactor = interactor
        self.window = window
        self.level = level
        self.colormap = colormap
        self.opacity_map = opacity_map

    def setup(self):
        if not self.dicom_dir or not os.path.exists(self.dicom_dir):
            raise ValueError(f"DICOM directory {self.dicom_dir} not found")
        # 读取DICOM数据，实际上是data source
        self.image_reader = vtk.vtkDICOMImageReader()
        self.image_reader.SetDirectoryName(self.dicom_dir)
        self.image_reader.Update()

        # 确保 renderer 已添加到 render_window
        renderers = [
            self.render_window.GetRenderers().GetItemAsObject(i)
            for i in range(self.render_window.GetRenderers().GetNumberOfItems())
        ]
        if self.renderer not in renderers:
            self.render_window.AddRenderer(self.renderer)

        # 确保 interactor 绑定了 render_window 并设置交互样式
        if self.interactor.GetRenderWindow() != self.render_window:
            self.interactor.SetRenderWindow(self.render_window)
        interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(interactor_style)

        # 这里使用系统自动选择，如果是GPU服务器的话，可以直接选择用GPU去生成， mapper构建
        volume_mapper = vtk.vtkSmartVolumeMapper()
        volume_mapper.SetInputConnection(self.image_reader.GetOutputPort())

        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(volume_mapper)

        volume_property = vtk.vtkVolumeProperty()

        # 设置colormap
        color_func = vtk.vtkColorTransferFunction()
        if self.colormap is not None:
            for pt in self.colormap:
                if len(pt) == 4:
                    value, r, g, b = pt
                    color_func.AddRGBPoint(value, r, g, b)
        else:
            # 默认灰阶
            color_func.AddRGBPoint(0, 0.0, 0.0, 0.0)
            color_func.AddRGBPoint(1000, 1.0, 1.0, 1.0)

        volume_property.SetColor(color_func)

        # 设置opacity
        opacity_func = vtk.vtkPiecewiseFunction()
        if self.opacity_map is not None:
            for pt in self.opacity_map:
                if len(pt) == 2:
                    value, opacity = pt
                    opacity_func.AddPoint(value, opacity)
        else:
            opacity_func.AddPoint(0, 0.0)
            opacity_func.AddPoint(1000, 1.0)
        volume_property.SetScalarOpacity(opacity_func)

        # 设置窗宽窗位（通过调整color/opacity transfer function实现窗宽窗位）
        min_val = self.level - self.window / 2
        max_val = self.level + self.window / 2
        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
        color_func.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
        volume_property.SetColor(color_func)

        opacity_func = vtk.vtkPiecewiseFunction()
        opacity_func.AddPoint(min_val, 0.0)
        opacity_func.AddPoint(max_val, 1.0)
        volume_property.SetScalarOpacity(opacity_func)

        self.volume.SetProperty(volume_property)

        self.renderer.AddVolume(self.volume)
        self.renderer.ResetCamera()
    # 优化：去除此处的 self.render_window.Render()，统一在 RendererPicker 渲染

    # 调窗调用
    def set_window_level(self, window, level):
        """设置窗宽窗位"""
        self.window = window
        self.level = level
        if self.volume is not None:
            prop = self.volume.GetProperty()
            # vtkVolumeProperty 没有 SetColorWindow/SetColorLevel 方法
            # 需要通过调整 color/opacity transfer function 或重新设置属性
            # 这里简单实现为重新设置 colormap 和 opacity_map
            # 你可以根据需要自定义窗宽窗位的映射方式
            # 例如，线性拉伸灰度范围
            color_func = vtk.vtkColorTransferFunction()
            min_val = self.level - self.window / 2
            max_val = self.level + self.window / 2
            color_func.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
            color_func.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
            prop.SetColor(color_func)

            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(min_val, 0.0)
            opacity_func.AddPoint(max_val, 1.0)
            prop.SetScalarOpacity(opacity_func)

            if self.render_window is not None:
                self.render_window.Render()

    # 设置传输样条曲线
    def set_colormap(self, colormap):
        """设置伪彩色映射，colormap为[(value, r, g, b), ...]"""
        self.colormap = colormap
        if self.volume is not None:
            color_func = vtk.vtkColorTransferFunction()
            for pt in colormap:
                if len(pt) == 4:
                    value, r, g, b = pt
                    color_func.AddRGBPoint(value, r, g, b)
            prop = self.volume.GetProperty()
            prop.SetColor(color_func)
            if self.render_window is not None:
                self.render_window.Render()

    # 设置不透明度映射
    def set_opacity_map(self, opacity_map):
        """设置不透明度映射，opacity_map为[(value, opacity), ...]"""
        self.opacity_map = opacity_map
        if self.volume is not None:
            opacity_func = vtk.vtkPiecewiseFunction()
            for pt in opacity_map:
                if len(pt) == 2:
                    value, opacity = pt
                    opacity_func.AddPoint(value, opacity)
            prop = self.volume.GetProperty()
            prop.SetScalarOpacity(opacity_func)
            if self.render_window is not None:
                self.render_window.Render()

    def get_render_window(self):
        return self.render_window

    def clear(self):
        """只移除本类创建的 volume，不影响其他渲染内容"""
        if self.volume is not None and self.renderer is not None:
            self.renderer.RemoveVolume(self.volume)
            self.volume = None
        if self.render_window is not None:
            self.render_window.Render()


class _WebVR(ServerProtocol):

    view = None
    authKey = "wslink-secret"
    vr_render = None

    def initialize(self):
        # 设置交互协议
        self.registerVtkWebProtocol(protocols.vtkWebMouseHandler())
        self.registerVtkWebProtocol(protocols.vtkWebViewPort())
        self.registerVtkWebProtocol(protocols.vtkWebPublishImageDelivery(decode=False))
        # 不需要这个协议
        # self.registerVtkWebProtocol(protocols.vtkWebViewPortGeometryDelivery())
        self.updateSecret(_WebVR.authKey)

        app = self.getApplication()
        if app and hasattr(app, "SetImageEncoding"):
            app.SetImageEncoding(0)
        else:
            import logging

            logging.warning(
                "getApplication() returned None or does not have SetImageEncoding"
            )

        # 初始化默认视图
        if not _WebVR.view:
            self.render_window = self.initRenderWindow()
            # 设置默认视图
            _WebVR.view = self.render_window

            # 注册视图到应用
            if app and hasattr(app, "GetObjectIdMap"):
                app.GetObjectIdMap().SetActiveObject("VIEW", self.render_window)
                print("视图已注册到应用")
            else:
                import logging

                logging.warning(
                    "getApplication() returned None or does not have GetObjectIdMap"
                )
            _WebVR.view.Render()

    def initRenderWindow(self):
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.SetOffScreenRendering(1)  # 启用离屏渲染
        self.render_window.AddRenderer(self.renderer)
        # 设置背景颜色为深灰色 (0.2, 0.2, 0.2)
        self.renderer.SetBackground(0.2, 0.2, 0.2)
        fps_callback = FPSCallback(self.render_window, self.renderer)
        self.render_window.AddObserver(vtk.vtkCommand.RenderEvent, fps_callback.execute)
        return self.render_window

    @exportRpc("app.action.start_render")
    def start_render(self, params):
        print(f"start_render: {params}")

        # 确保视图已初始化
        if not _WebVR.view:
            self.render_window = self.initRenderWindow()
            _WebVR.view = self.render_window

        # 创建VR渲染器
        if not self.vr_render:
            self.interactor = vtk.vtkRenderWindowInteractor()
            self.interactor.SetRenderWindow(_WebVR.view)
            interactor_style = vtk.vtkInteractorStyleTrackballCamera()
            self.interactor.SetInteractorStyle(interactor_style)

            self.vr_render = VRRender(
                params.get("dicom_dir"), _WebVR.view, self.renderer, self.interactor
            )
            self.vr_render.setup()

        self.renderer.ResetCamera()
        _WebVR.view.Render()
        self.force_refresh()

        return {"status": "started"}

    def force_refresh(self):
        app = self.getApplication()
        if app is not None:
            app.InvokeEvent("UpdateEvent")
        
    @exportRpc("app.action.clear_render")
    def clear_render(self):
        if self.vr_render:
            self.vr_render.clear()
            self.vr_render = None
        self.force_refresh()
        return {"status": "cleared"}

    # 调窗调用
    @exportRpc("app.action.set_window_level")
    def set_window_level(self, window, level):
        if self.vr_render:
            self.vr_render.set_window_level(window, level)
        self.force_refresh()
        return {"status": "set_window_level", "window": window, "level": level}

    # 设置样条曲线
    @exportRpc("app.action.set_colormap")
    def set_colormap(self, colormap):
        if self.vr_render:
            self.vr_render.set_colormap(colormap)
        self.force_refresh()
        return {"status": "set_colormap", "colormap": colormap}



# =============================================================================
# Main: Parse args and start server
# =============================================================================


if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description="VTK/Web Cone web-application")
    server.add_arguments(parser)
    args = parser.parse_args()
    _WebVR.authKey = args.authKey
    server.start_webserver(options=args, protocol=_WebVR)
