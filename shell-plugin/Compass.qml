import QtQuick

// Direction rose. North is up. Azimuth is degrees clockwise from north.
// The thin arrow is the track (where it appears → where it goes).
// big: also draw the arrow you should face.
Item {
  id: root

  property real startAz: 0
  property real endAz: 90
  property real lookAz: 0
  property bool big: false
  property int size: 88
  property color ink: "#dceaf2"
  property color ring: "#8aa0b0"
  property color muted: "#8aa0b0"

  implicitWidth: size
  implicitHeight: size

  function polar(az, radius) {
    var rad = az * Math.PI / 180
    return Qt.point(width / 2 + Math.sin(rad) * radius, height / 2 - Math.cos(rad) * radius)
  }

  function head(ctx, x1, y1, x2, y2, length) {
    var ang = Math.atan2(y2 - y1, x2 - x1)
    ctx.beginPath()
    ctx.moveTo(x2, y2)
    ctx.lineTo(x2 - length * Math.cos(ang - 0.45), y2 - length * Math.sin(ang - 0.45))
    ctx.lineTo(x2 - length * Math.cos(ang + 0.45), y2 - length * Math.sin(ang + 0.45))
    ctx.closePath()
    ctx.fill()
  }

  function repaint() {
    canvas.requestPaint()
  }

  onStartAzChanged: repaint()
  onEndAzChanged: repaint()
  onLookAzChanged: repaint()
  onBigChanged: repaint()
  onInkChanged: repaint()
  onWidthChanged: repaint()
  onHeightChanged: repaint()
  Component.onCompleted: repaint()

  Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true

    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      var cx = width / 2
      var cy = height / 2
      var radius = Math.min(width, height) * 0.30

      ctx.strokeStyle = root.ring
      ctx.globalAlpha = 0.85
      ctx.lineWidth = Math.max(1, radius * 0.045)
      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.stroke()

      ctx.fillStyle = root.muted
      ctx.font = Math.max(9, Math.round(radius * 0.32)) + "px monospace"
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      var names = ["N", "E", "S", "W"]
      for (var i = 0; i < 4; i++) {
        var tick = root.polar(i * 90, radius)
        var label = root.polar(i * 90, radius * 1.28)
        ctx.globalAlpha = 0.9
        ctx.fillText(names[i], label.x, label.y)
        ctx.globalAlpha = 0.45
        ctx.beginPath()
        ctx.arc(tick.x, tick.y, Math.max(1.2, radius * 0.045), 0, Math.PI * 2)
        ctx.fill()
      }

      var from = root.polar(root.startAz, radius * 0.72)
      var to = root.polar(root.endAz, radius * 0.72)
      ctx.globalAlpha = 1
      ctx.strokeStyle = root.ink
      ctx.fillStyle = root.ink
      ctx.lineCap = "round"
      ctx.lineWidth = Math.max(1.5, radius * 0.055)
      ctx.beginPath()
      ctx.moveTo(from.x, from.y)
      ctx.lineTo(to.x, to.y)
      ctx.stroke()
      root.head(ctx, from.x, from.y, to.x, to.y, radius * 0.2)
      ctx.beginPath()
      ctx.arc(from.x, from.y, Math.max(2.2, radius * 0.075), 0, Math.PI * 2)
      ctx.fill()

      if (root.big) {
        var aim = root.polar(root.lookAz, radius * 0.9)
        ctx.lineWidth = Math.max(2.5, radius * 0.09)
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(aim.x, aim.y)
        ctx.stroke()
        root.head(ctx, cx, cy, aim.x, aim.y, radius * 0.28)
        ctx.beginPath()
        ctx.arc(cx, cy, Math.max(2, radius * 0.06), 0, Math.PI * 2)
        ctx.fill()
      }
    }
  }
}
