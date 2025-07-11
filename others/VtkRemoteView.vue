<template>
    <div class="vtk-remote-view">
        <div class="vtk-controls">
            <button @click="startVRRender()">渲染CT数据 (Volume)</button>
            <button @click="clearRender()">清除渲染</button>
        </div>
        <div ref="divRenderer" class="vtk-remote-view-container"></div>
    </div>
</template>

<script>
import vtkWSLinkClient from '@kitware/vtk.js/IO/Core/WSLinkClient';
import SmartConnect from 'wslink/src/SmartConnect';
import vtkRemoteView from '@kitware/vtk.js/Rendering/Misc/RemoteView';

// 在 Vue 组件外部设置 SmartConnect，只需执行一次
vtkWSLinkClient.setSmartConnectClass(SmartConnect);
export default {
    name: 'VtkRemoteView',
    data() {
        return {
            divRenderer: null,
            // 连接和视图状态
            connection: null,
            view: null,
            // UI 状态
            loading: false,
            statusMessage: '请选择一个渲染类型来启动连接',
            // 连接配置
            config: {
                // 确保这里的 URL 和端口与你的服务端启动命令一致
                sessionURL: 'ws://localhost:8888/ws',
            },
            // 连接状态
            validClient: null,
            // 会话状态
            validSession: null,
            // 远端view
            remoteView: null,
        }
    },
    methods: {
        // 在这里添加你的方法
        init() {
            // 承载容器
            this.divRenderer = this.$refs.divRenderer;
            // 实例化连接对象
            this.clientToConnect = vtkWSLinkClient.newInstance();
        },
        startVRRender() {
            if (!this.validSession) return;
            this.validSession.call('app.action.start_render', [{
                dicom_dir: "data/81344", // 包含 renderType: 'cone', 'sphere', 或 'volume'
                userId: 'vue-client-user' // 可以传递其他任何需要的参数
            }]).then(result => {
                console.log(result);
            });
        },
        async startRendering(params) {
            if (this.loading) return; // 防止重复点击

            this.loading = true;
            this.statusMessage = `正在请求渲染: ${params.renderType}...`;

            // --- 1. 清理旧的连接和视图，为新渲染做准备 ---
            // this.cleanup();

            try {
                this.validSession.call('app.action.start_render', [{
                    dicom_dir: "data/81344", // 包含 renderType: 'cone', 'sphere', 或 'volume'
                    userId: 'vue-client-user' // 可以传递其他任何需要的参数
                }]).then(result => {
                    console.log(result);
                });
            } catch (error) {
                console.error('渲染设置失败:', error);
                this.statusMessage = `错误: ${error.message}`;
            } finally {
                this.loading = false;
            }
        },

        handleError(httpReq) {
            // 添加连接错误函数
            const message =
                (httpReq && httpReq.response && httpReq.response.error) ||
                `Connection error`;
            console.error(message);
            console.log(httpReq);
        },
        handleClose(httpReq) {
            const message =
                (httpReq && httpReq.response && httpReq.response.error) ||
                `Connection close`;
            console.error(message);
            console.log(httpReq);
        },
        clearRender() {
            if (this.validSession) {
                this.validSession.call('app.action.clear_render', []).then(result => {
                    console.log(result);
                });
            }
        },
        onResize() {
            if (this.view) {
                this.view.resize();
            }
        },
        cleanup() {
            // 清理视图
            if (this.view) {
                window.removeEventListener('resize', this.onResize);
                this.view.delete();
                this.view = null;
            }
            // 清理连接
            if (this.connection) {
                this.connection.destroy(1000);
                this.connection = null;
            }
            // 清理DOM
            if (this.$refs.divRenderer) {
                this.$refs.divRenderer.innerHTML = '';
            }
        }
    },
    async mounted() {
        this.init();
        //初始化连接函数
        this.clientToConnect.onConnectionError(this.handleError);
        // this.clientToConnect.onClose(this.handleClose);
        this.validClient = await this.clientToConnect.connect(this.config);
        //初始化流的设置和远端view
        const viewStream = this.clientToConnect.getImageStream().createViewStream('-1');
        this.remoteView = vtkRemoteView.newInstance({
            rpcWheelEvent: 'viewport.mouse.zoom.wheel',
            viewStream,
        });
        //初始化会话
        this.validSession = this.validClient.getConnection().getSession();
        //TODO 需要设置用户session信息，多用户时需要做隔离，后台需要对同一个渲染类做lru缓存
        this.remoteView.setSession(this.validSession);
        //承载容器
        this.remoteView.setContainer(this.divRenderer);
        //设置交互比例和质量
        this.remoteView.setInteractiveRatio(0.7);
        //设置交互质量
        this.remoteView.setInteractiveQuality(50);
        //监听窗口大小变化
        window.addEventListener('resize', this.remoteView.resize);
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

.vtk-controls {
    padding: 15px;
    background: #fff;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-shrink: 0;
}

.vtk-controls button {
    padding: 10px 20px;
    font-size: 16px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    background-color: #007bff;
    color: white;
    transition: background-color 0.3s ease;
}

.vtk-controls button:hover {
    background-color: #0056b3;
}

.vtk-controls button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
}
</style>
