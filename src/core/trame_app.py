from trame.decorators import TrameApp
from trame.app import get_server
from trame_server import Server
from trame_server.state import State
from render.dicom_render import VTKVolumeVisualizer
from typing import Literal
@TrameApp("trame-server-app")
class TrameServerApp:
    # trame server 实例
    server: Server | None = None
    # trame state 实例
    state: State | None = None

    def __init__(self, client_type: Literal["vue2", "vue3"] = "vue2"):
        # 获取 trame 服务器实例，名称与装饰器一致
        self.server = get_server(name="trame-server-app", client_type = client_type)
        if self.server is None:
            raise Exception("Failed to get trame server instance")
        self.state = self.server.state
        if self.state is None:
            raise Exception("Failed to get trame server state instance")
        print("self.state", self.state)
        self.dicom_dir = None  # 初始不设置路径，由客户端传递
        self.visualizer = None
        self.setup_state()
        self.setup_callbacks()

    def setup_state(self):
        assert self.state is not None, "Trame server/state 未初始化"
        # 初始化共享状态
        with self.state as state:
            state.render_data = None  # 用于存储渲染结果
            state.render_status = "idle"  # 渲染状态：idle, processing, done
            state.dicom_dir = ""  # 新增：由客户端传递 DICOM 路径

    def setup_callbacks(self):
        assert self.server is not None and self.state is not None, "Trame server/state 未初始化"
        @self.state.change("dicom_dir")
        def on_dicom_dir_change(dicom_dir, **kwargs):
            if not dicom_dir:
                print("未提供 DICOM 路径")
                return
            print(f"收到客户端 DICOM 路径: {dicom_dir}")
            self.dicom_dir = dicom_dir
            # 重新初始化可视化器
            self.visualizer = VTKVolumeVisualizer(self.server, self.dicom_dir)
            self.visualizer.bind_ui()
            print("已根据新路径初始化 VTKVolumeVisualizer")

        @self.state.change("reset_camera")
        def reset_camera(**kwargs):
            if self.visualizer:
                self.visualizer.reset_camera()

        @self.state.change("update_opacity")
        def update_opacity(opacity_scale, **kwargs):
            if not self.visualizer:
                return
            volumes = self.visualizer.renderer.GetVolumes()
            if volumes.GetNumberOfItems() > 0:
                volume = volumes.GetItemAsObject(0)
                from vtkmodules.vtkRenderingCore import vtkVolume
                if isinstance(volume, vtkVolume):
                    opacity_func = volume.GetProperty().GetScalarOpacity()
                    for i in range(opacity_func.GetSize()):
                        current_value = opacity_func.GetNodeValue(i)
                        opacity_func.RemovePoint(current_value)
                        opacity_func.AddPoint(current_value, min(1.0, current_value * opacity_scale))
                    if self.visualizer.vtk_view:
                        self.visualizer.vtk_view.update()
                        self.visualizer.render_window.Render()

        def update_interaction():
            if self.visualizer and self.visualizer.vtk_view:
                self.visualizer.vtk_view.update()
                self.visualizer.render_window.Render()
                print("交互更新，强制刷新")

        if hasattr(self.state, "on_change") and callable(self.state.on_change):
            self.state.on_change("*", update_interaction)
        else:
            print("警告: server.state.on_change 不可用，交互事件未绑定")

    def start(self, port=8080, host="0.0.0.0"):
        if self.server is None:
            raise Exception("Failed to get trame server instance")
        self.server.start(
            port=port,
            host=host,
            open_browser=False,
            show_connection_info=True
        )

if __name__ == "__main__":
    app = TrameServerApp()
    app.start()