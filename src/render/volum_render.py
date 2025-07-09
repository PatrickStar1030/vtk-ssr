import vtk
import os
from functools import lru_cache

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

class VolumRender:
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