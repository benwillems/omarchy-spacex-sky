import QtQuick
import qs.Commons

Rectangle {
  id: root

  property string message: ""

  readonly property color fg: Color.popups.text

  visible: message !== ""
  width: parent ? parent.width : implicitWidth
  radius: Math.max(Style.cornerRadius, 14)
  color: Qt.rgba(fg.r, fg.g, fg.b, 0.05)
  implicitHeight: label.implicitHeight + Style.space(28)

  Text {
    id: label
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
    anchors.leftMargin: Style.space(16)
    anchors.rightMargin: Style.space(16)
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.WordWrap
    text: root.message
    textFormat: Text.PlainText
    color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.82)
    font.family: Style.font.family
    font.pixelSize: Style.font.body
  }
}
