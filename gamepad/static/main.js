$(document).ready(function(){
    var socket = io.connect("http://" + document.domain + ":" + location.port + "/ctl");
    socket.on("connect", function() {
	console.log("Socket connected.")
	socket.emit("ctl", {"key": "right", "state": true});
    });
});
