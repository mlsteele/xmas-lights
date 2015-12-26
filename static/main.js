$(document).ready(function(){
  var socket = io.connect(location.protocol + "//" + document.domain + ":" + location.port + "/ctl");
  socket.on("connect", function() {
    console.log("Socket connected.")
  });

  function emit_update(key, state) {
    socket.emit("ctl", {"key": key, "state": state});
  }

  var btn_left = $(".btn-left");
  var btn_right = $(".btn-right");

  btn_left.on("touchstart", function(e) {
    e.preventDefault();
    emit_update("left", true);
  })
  btn_left.on("touchend touchcancel", function(e) {
    e.preventDefault();
    emit_update("left", false);
  });

  btn_right.on("touchstart", function(e) {
    e.preventDefault();
    emit_update("right", true);
  })
  btn_right.on("touchend touchcancel", function(e) {
    e.preventDefault();
    emit_update("right", false);
  });
});
