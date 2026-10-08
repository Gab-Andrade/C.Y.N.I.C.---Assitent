var ws = new WebSocket("ws://localhost:8000/ws");
var statusDiv = document.getElementById('status');
var containerDiv = document.getElementById('core-container');

ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    statusDiv.innerHTML = data.mensagem;
    
    if(data.estado === "ouvindo" || data.estado === "processando" || data.estado === "respondendo") {
        containerDiv.classList.add("active");
    } else {
        containerDiv.classList.remove("active");
    }
};