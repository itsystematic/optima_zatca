import { io } from "socket.io-client";

import {
    default_site,
    socketio_port,
} from "../../../sites/common_site_config.json";


const initSocket = () => {
    let host = window.location.hostname;
    let port = window.location.port ? `:${socketio_port}` : '';
    let protocol = port ? 'http' : 'https';

    let siteName = default_site;


    let url = `${protocol}://${host}${port}/${siteName}`;

    console.log('Connecting to socket at', url);


    const socket = io(url, {
        withCredentials: true,
        reconnectionAttempts: 5
    })





    return socket;
}


export const socket = initSocket();
