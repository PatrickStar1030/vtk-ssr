<template>
    <div class="vtk-remote-view">
        <div ref="divRenderer" class="vtk-remote-view-container"></div>
    </div>
</template>

<script>
import vtkWSLinkClient from '@kitware/vtk.js/IO/Core/WSLinkClient';
import SmartConnect from 'wslink/src/SmartConnect';
import vtkRemoteView from '@kitware/vtk.js/Rendering/Misc/RemoteView';
export default {
    name: 'VtkRemoteView',
    data() {
        return {
            divRenderer: null,
            clientToConnect: null,
            config: {
                application: 'cone',
                sessionURL: 'ws://localhost:8888/ws',
            }
        }
    },
    methods: {
        // 在这里添加你的方法
        init() {
            // 承载容器
            this.divRenderer = this.$refs.divRenderer;
            // 设置智能连接类
            vtkWSLinkClient.setSmartConnectClass(SmartConnect);
            // 实例化连接对象
            this.clientToConnect = vtkWSLinkClient.newInstance();
        }
    },
    mounted() {
        this.init();
        //初始化连接函数
    
        this.clientToConnect
            .connect(this.config)
            .then((validClient) => {
                const viewStream = this.clientToConnect.getImageStream().createViewStream('-1');
                const view = vtkRemoteView.newInstance({
                    rpcWheelEvent: 'viewport.mouse.zoom.wheel',
                    viewStream,
                });
                const session = validClient.getConnection().getSession();
                session.set('user', 'admin');
                session.set('sessionId', '1234567890');
                //TODO 需要设置用户session信息，多用户时需要做隔离，后台需要对同一个渲染类做lru缓存
                view.setSession(session);
                //承载容器
                view.setContainer(this.divRenderer);
                view.setInteractiveRatio(0.7); // the scaled image compared to the clients view resolution
                view.setInteractiveQuality(50); // jpeg quality
                window.addEventListener('resize', view.resize);
            })
            .catch((error) => {
                console.error(error);
            });
        // 添加连接错误函数
        this.clientToConnect.onConnectionError((httpReq) => {
            const message =
                (httpReq && httpReq.response && httpReq.response.error) ||
                `Connection error`;
            console.error(message);
            console.log(httpReq);
        });
        // close
        this.clientToConnect.onClose((httpReq) => {
            const message =
                (httpReq && httpReq.response && httpReq.response.error) ||
                `Connection close`;
            console.error(message);
            console.log(httpReq);
        });
    }
}
</script>

<style scoped>
.vtk-remote-view {
    padding: 20px;
    text-align: center;
}
.vtk-remote-view-container {
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    position: relative;
}
</style>
