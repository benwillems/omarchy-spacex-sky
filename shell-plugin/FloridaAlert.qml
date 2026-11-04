import QtQuick
import qs.Commons
import qs.Ui
import "Sky.js" as Sky

// The next Florida launch, shown when it is not already the hero card.
Rectangle {
  id: root

  property var event: null
  property double nowMs: 0

  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  clip: true
  radius: Math.max(Style.cornerRadius, 14)
  color: Qt.rgba(fg.r, fg.g, fg.b, 0.07)
  border.width: 1
  border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.28)
  implicitHeight: body.implicitHeight + Style.space(24)

  Rectangle {
    anchors.left: parent.left
    anchors.top: parent.top
    anchors.bottom: parent.bottom
    width: Style.space(4)
    color: root.fg
  }

  Column {
    id: body
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(12)
    spacing: Style.space(3)

    Text {
      text: root.event && root.event.pad_label
            ? ("FLORIDA LAUNCH  ·  " + root.event.pad_label)
            : "FLORIDA LAUNCH"
      textFormat: Text.PlainText
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 1.2
    }

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
      text: root.event ? root.event.mission : ""
      textFormat: Text.PlainText
      elide: Text.ElideRight
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.bold: true
    }

    Text {
      width: parent.width
      text: root.event
            ? (root.event.day + "  " + root.event.clock + "   ·   "
               + Sky.lead(root.event.epoch, root.nowMs, root.event.time_set))
            : ""
      textFormat: Text.PlainText
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
    }

    Text {
      width: parent.width
      visible: root.event && root.event.can_we_see
      text: root.event ? ("Can we see it?  " + root.event.can_we_see) : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
    }
  }
}
