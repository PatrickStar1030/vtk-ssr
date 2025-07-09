from vtkmodules.web import wslink as vtk_wslink
from vtkmodules.web import protocols
from wslink import server
import argparse
import logging
import vtk

from enum import Enum

class RenderEnum(Enum):
    SLICE = 1
    VR = 2


class Server(vtk_wslink.ServerProtocol):
    renderType = RenderEnum.SLICE
    resourcePath: str
    view = None
    authKey = None
    dataSource = None

    def initialize(self):
        global renderer, renderWindow, renderWindowInteractor, cone, mapper, actor

        # 获取用户操作交互对象
        self.registerVtkWebProtocol(protocols.vtkWebMouseHandler())
        self.registerVtkWebProtocol(protocols.vtkWebViewPort())
        # 设置传输协议
        self.registerVtkWebProtocol(protocols.vtkWebPublishImageDelivery(decode=False))
        self.registerVtkWebProtocol(protocols.vtkWebViewPortGeometryDelivery())

        # 更新认证密钥
        self.updateSecret(Server.authKey)

        # 设置图像编码
        app = self.getApplication()
        if app is not None and hasattr(app, "SetImageEncoding"):
            app.SetImageEncoding(0)
        else:
            import logging
            logging.warning("获取客户端对象失败")
        
        if not Server.view:
            Server.view = vtk.vtkRenderWindow()
            renderer = vtk.vtkRenderer()
            renderWindow = vtk.vtkRenderWindow()
            renderWindow.AddRenderer(renderer)

            renderWindowInteractor = vtk.vtkRenderWindowInteractor()
            renderWindowInteractor.SetRenderWindow(renderWindow)
            # 设置交互样式为 TrackballCamera
            interactor_style = vtk.vtkInteractorStyleTrackballCamera()
            renderWindowInteractor.SetInteractorStyle(interactor_style)












        if self.renderType is None:
            logging.error("渲染类型未设置")
        
        if self.resourcePath is None:
            logging.error("资源路径未设置")

        if self.renderType == RenderEnum.SLICE:
            self.dataSource = slice_render()
        elif self.renderType == RenderEnum.VR:
            self.dataSource =