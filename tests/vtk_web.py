from ast import parse
import sys
import os

# import vtk modules.
import vtk
from vtkmodules.web import protocols
from vtkmodules.web import wslink as vtk_wslink
from wslink import server

import argparse

# =============================================================================
# Create custom ServerProtocol class to handle clients requests
# =============================================================================


class _WebCone(vtk_wslink.ServerProtocol):

    # Application configuration
    view = None
    authKey = "wslink-secret"

    def initialize(self):
        global renderer, renderWindow, renderWindowInteractor, cone, mapper, actor

        # Bring used components
        self.registerVtkWebProtocol(protocols.vtkWebMouseHandler())
        self.registerVtkWebProtocol(protocols.vtkWebViewPort())
        self.registerVtkWebProtocol(protocols.vtkWebPublishImageDelivery(decode=False))
        self.registerVtkWebProtocol(protocols.vtkWebViewPortGeometryDelivery())

        # Update authentication key to use
        self.updateSecret(_WebCone.authKey)

        # tell the C++ web app to use no encoding.
        # ParaViewWebPublishImageDelivery must be set to decode=False to match.
        app = self.getApplication()
        if app is not None and hasattr(app, "SetImageEncoding"):
            app.SetImageEncoding(0)
        else:
            import logging
            logging.warning("getApplication() returned None or does not have SetImageEncoding")
        
        if not _WebCone.view:
            # VTK specific code
            renderer = vtk.vtkRenderer()
            renderWindow = vtk.vtkRenderWindow()
            renderWindow.AddRenderer(renderer)

            renderWindowInteractor = vtk.vtkRenderWindowInteractor()
            renderWindowInteractor.SetRenderWindow(renderWindow)
            # 设置交互样式为 TrackballCamera
            # renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()
            interactor_style = vtk.vtkInteractorStyleTrackballCamera()
            renderWindowInteractor.SetInteractorStyle(interactor_style)


            # TODO 添加枚举类，根据枚举类创建不同的渲染器
            cone = vtk.vtkConeSource()
            mapper = vtk.vtkPolyDataMapper()
            actor = vtk.vtkActor()

            mapper.SetInputConnection(cone.GetOutputPort())
            actor.SetMapper(mapper)

            renderer.AddActor(actor)
            renderer.ResetCamera()
            renderWindow.Render()

            # VTK Web application specific
            _WebCone.view = renderWindow
            app = self.getApplication()
            if app is not None:
                app.GetObjectIdMap().SetActiveObject("VIEW", renderWindow)

    # TODO 添加事件注册，根据不同的action响应数据到前端
    # TODO 用户session管理
# =============================================================================
# Main: Parse args and start server
# =============================================================================


if __name__ == "__main__":
        # Create argument parser
    parser = argparse.ArgumentParser(
        description="VTK/Web Cone web-application")

    # Add default arguments
    server.add_arguments(parser)

    # Extract arguments
    args = parser.parse_args()

    # Configure our current application
    _WebCone.authKey = args.authKey

    # Start server
    server.start_webserver(options=args, protocol=_WebCone)