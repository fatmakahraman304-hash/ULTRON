import {sceneIntent} from './intents';
(window as unknown as {ULTRONSceneIntents:{resolve:typeof sceneIntent}}).ULTRONSceneIntents={resolve:sceneIntent};
