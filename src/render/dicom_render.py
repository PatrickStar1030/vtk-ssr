import vtk
import pydicom
import os
import numpy as np
from functools import lru_cache
from trame.widgets import vuetify3 as vuetify, vtk as vtk_widgets
from trame.ui.vuetify3 import SinglePageLayout
from trame_server import Server

# 缓存 DICOM 数据
@lru_cache(maxsize=1)
def read_dicom_series(dicom_dir):
    """读取并缓存 DICOM 序列"""
    if not os.path.exists(dicom_dir):
        raise FileNotFoundError(f"DICOM 目录 {dicom_dir} 不存在")
    files = [f for f in os.listdir(dicom_dir) if f.endswith(".dcm")]
    if not files:
        raise ValueError(f"DICOM 目录 {dicom_dir} 不包含 .dcm 文件")
    
    reader = vtk.vtkDICOMImageReader()
    reader.SetDirectoryName(dicom_dir)
    reader.Update()
    image_data = reader.GetOutput()
    
    if image_data.GetNumberOfPoints() == 0:
        raise ValueError("DICOM 数据为空，请检查文件格式或路径")
    
    dims = image_data.GetDimensions()
    print(f"DICOM 数据维度: {dims}")
    return image_data

# 解析 DICOM 元数据
def parse_dicom_metadata(dicom_dir):
    """解析 DICOM 文件的元数据"""
    metadata = []
    for file_name in os.listdir(dicom_dir):
        if file_name.endswith(".dcm"):
            file_path = os.path.join(dicom_dir, file_name)
            ds = pydicom.dcmread(file_path)
            metadata.append({
                "PatientID": ds.get("PatientID", "N/A"),
                "PixelSpacing": ds.get("PixelSpacing", "N/A"),
                "SliceThickness": ds.get("SliceThickness", "N/A"),
                "Rows": ds.Rows,
                "Columns": ds.Columns
            })
    print(f"解析到 {len(metadata)} 个 DICOM 文件的元数据")
    return metadata

class VTKVolumeVisualizer:
    def __init__(self, server, data_source):
        if server is None:
            raise ValueError("Server 对象为 None")
        self.server = server
        self.data_source = data_source
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        
        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)
        self.interactor.Initialize()
        self.render_window.SetOffScreenRendering(1)
        
        # 启用交互样式
        self.interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(self.interactor_style)
        
        self.renderer.SetBackground(0.0, 0.0, 0.1)  # 更暗背景，提升对比度
        self.image_data = read_dicom_series(self.data_source) if isinstance(self.data_source, str) else self.data_source
        self.setup_pipeline()

    def setup_pipeline(self):
        # 配置体渲染管道
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputData(self.image_data)

        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # 获取数据范围
        scalar_range = self.image_data.GetScalarRange()
        print(f"数据标量范围: {scalar_range}")

        # 优化转移函数（增强粉红和自然肤色）
        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(scalar_range[0], 0.0, 0.0, 0.0)     # 最低值（黑色）
        color_func.AddRGBPoint(-500, 0.1, 0.1, 0.1)               # 空气/肺部（极暗灰）
        color_func.AddRGBPoint(0, 0.9, 0.8, 0.8)                  # 软组织（浅粉）
        color_func.AddRGBPoint(100, 1.0, 0.8, 0.8)                # 低密度肌肉（粉红）
        color_func.AddRGBPoint(300, 1.0, 0.7, 0.7)                # 肌肉（深粉）
        color_func.AddRGBPoint(1000, 1.0, 1.0, 1.0)               # 骨骼（白色）
        color_func.AddRGBPoint(scalar_range[1], 0.9, 0.6, 0.6)    # 最高值（淡粉）
        volume_property.SetColor(color_func)

        opacity_func = vtk.vtkPiecewiseFunction()
        opacity_func.AddPoint(scalar_range[0], 0.0)               # 最低值透明
        opacity_func.AddPoint(-500, 0.15)                        # 空气适中不透明
        opacity_func.AddPoint(0, 0.6)                            # 软组织高不透明
        opacity_func.AddPoint(100, 0.7)                          # 低密度肌肉高不透明
        opacity_func.AddPoint(300, 0.8)                          # 肌肉高不透明
        opacity_func.AddPoint(1000, 0.9)                         # 骨骼高不透明
        opacity_func.AddPoint(scalar_range[1], 0.8)           # 最高值高不透明
        volume_property.SetScalarOpacity(opacity_func)

        # 创建体对象
        volume = vtk.vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)

        # 优化光源
        light = vtk.vtkLight()
        light.SetPosition(1, 1, 1)  # 更自然的光源位置
        light.SetIntensity(1.5)     # 增加光强
        self.renderer.AddLight(light)

        # 添加到渲染器
        self.renderer.AddVolume(volume)
        self.renderer.ResetCamera()

        # 设置渲染窗口
        self.render_window.SetSize(1024, 1024)
        self.render_window.Render()
        print(f"体渲染初始化完成，窗口尺寸: 1024x1024")

        # 初始化状态
        self.server.state.update({
            "slice_max": 0  # 禁用滑动条，体渲染无需切片
        })
        print("状态初始化: 体渲染模式")
        self.vtk_view = None

    def reset_camera(self):
        self.renderer.ResetCamera()
        if self.vtk_view:
            self.vtk_view.update()
            print("相机已重置，强制更新")
            self.render_window.Render()

    def update_slice(self, slice_idx):
        # 体渲染无需更新切片，保持空实现
        pass

    def bind_ui(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("DICOM 体渲染查看器")
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VBtn("重置视角", click="trigger('reset_camera')", icon="mdi-crop-free")
                vuetify.VSlider(
                    v_model=("opacity_scale", 1.0),
                    min=0.1,
                    max=2.0,
                    step=0.1,
                    label="不透明度缩放",
                    hide_details=True,
                    dense=True,
                    style="max-width: 300px;",
                    change="trigger('update_opacity', $event)",
                )
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="pa-0 fill-height", style="width: 100vw; height: 100vh;"):
                    self.vtk_view = vtk_widgets.VtkRemoteView(
                        self.render_window,
                        interactive_ratio=1.0,
                        style="width: 100%; height: 100%;",
                    )
                    self.vtk_view.update()
                    print("VtkRemoteView 初始化完成 (体渲染)")

class DicomRenderer:
    def __init__(self, server: Server):
        self.server = server
        self.reader = None
        self.volume = None
        self.setup_renderer()

    def setup_renderer(self):
        # 示例：读取 DICOM 文件并设置体渲染
        self.reader = vtk.vtkDICOMImageReader()
        # 假设 DICOM 文件路径由前端传入，实际路径需动态设置
        # self.reader.SetDirectoryName("path/to/dicom/folder")
        self.reader.Update()

        # 创建体渲染管道
        # 智能创建渲染管道
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        # volume_mapper = vtk.vtkSmartVolumeMapper()
        volume_mapper.SetInputConnection(self.reader.GetOutputPort())

        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(volume_mapper)

        # 设置体渲染属性（透明度、颜色等）
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # 示例：简单灰度映射
        opacity_transfer = vtk.vtkPiecewiseFunction()
        opacity_transfer.AddPoint(0, 0.0)
        opacity_transfer.AddPoint(255, 1.0)
        volume_property.SetScalarOpacity(opacity_transfer)

        color_transfer = vtk.vtkColorTransferFunction()
        color_transfer.AddRGBPoint(0, 0.0, 0.0, 0.0)
        color_transfer.AddRGBPoint(255, 1.0, 1.0, 1.0)
        volume_property.SetColor(color_transfer)

        self.volume.SetProperty(volume_property)

    def render_dicom(self, dicom_path: str):
        # 更新 DICOM 文件路径并触发渲染
        with self.server.state as state:
            state.render_status = "processing"
            try:
                if self.reader is None:
                    raise Exception("Reader is not initialized")
                self.reader.SetDirectoryName(dicom_path)
                self.reader.Update()
                state.render_data = {
                    "volume": self.volume,  # 传递 VTK 对象给前端
                    "status": "success"
                }
                state.render_status = "done"
            except Exception as e:
                state.render_data = {"error": str(e)}
                state.render_status = "error"

    @property
    def state(self):
        return self.server.state