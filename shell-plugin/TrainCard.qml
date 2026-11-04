import QtQuick
import qs.Commons
import "Sky.js" as Sky

Rectangle {
  id: root

  property var event: null
  property double nowMs: 0

  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  clip: true
  radius: Math.max(Style.cornerRadius, 14)
  color: Qt.rgba(fg.r, fg.g, fg.b, 0.045)
  border.width: 1
  border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.12)
  implicitHeight: body.implicitHeight + Style.space(24)

  Column {
    id: body
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(12)
    spacing: Style.space(6)

    Text {
      width: parent.width
      text: root.event
            ? ("★  " + root.event.date_label + "  ·  " + root.event.clock
               + "   ·   " + Sky.lead(root.event.epoch, root.nowMs, true))
            : ""
      textFormat: Text.PlainText
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.title
      font.bold: true
    }

    Row {
      width: parent.width
      spacing: Style.space(12)

      Compass {
        id: rose
        size: Style.space(84)
        startAz: root.event ? root.event.start_az : 0
        endAz: root.event ? root.event.end_az : 0
        lookAz: root.event ? (root.event.look_az || root.event.start_az) : 0
        ink: root.accent
        ring: root.muted
        muted: root.muted
      }

      Column {
        width: parent.width - rose.width - parent.spacing
        spacing: Style.space(3)

        Text {
          width: parent.width
          text: root.event ? root.event.where : ""
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
        }

        Text {
          width: parent.width
          text: root.event
                ? ("Appears " + root.event.start_dir + "  →  goes " + root.event.end_dir)
                : ""
          textFormat: Text.PlainText
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          width: parent.width
          text: root.event
                ? ("Peak " + root.event.peak_fists + " above the horizon (" + root.event.peak_alt + "°)")
                : ""
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.font.body
        }

        Text {
          width: parent.width
          text: root.event ? root.event.duration : ""
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.muted
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
        }
      }
    }

    Text {
      width: parent.width
      text: root.event ? (root.event.kid_line || "") : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
    }

    Text {
      width: parent.width
      text: root.event ? (root.event.note || "") : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }
}
