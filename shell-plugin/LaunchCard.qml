import QtQuick
import qs.Commons
import qs.Ui
import "Sky.js" as Sky

Rectangle {
  id: root

  property var event: null
  property double nowMs: 0

  signal favoriteToggled(string siteId)

  readonly property bool fav: event && event.favorite === true
  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  clip: true
  radius: Math.max(Style.cornerRadius, 14)
  color: fav ? Qt.rgba(accent.r, accent.g, accent.b, 0.13) : Qt.rgba(fg.r, fg.g, fg.b, 0.045)
  border.width: fav ? 2 : 1
  border.color: fav ? Qt.rgba(accent.r, accent.g, accent.b, 0.85) : Qt.rgba(fg.r, fg.g, fg.b, 0.12)
  implicitHeight: body.implicitHeight + Style.space(24)

  Column {
    id: body
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(12)
    spacing: Style.space(3)

    Item {
      width: parent.width
      height: Math.max(placeRow.implicitHeight, Style.space(22))

      Row {
        id: placeRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(8)

        Rectangle {
          radius: height / 2
          color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.08)
          border.width: 1
          border.color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.2)
          implicitWidth: badge.implicitWidth + Style.space(14)
          implicitHeight: badge.implicitHeight + Style.space(6)

          Text {
            id: badge
            anchors.centerIn: parent
            text: root.event ? (root.event.region_name || root.event.region || "").toUpperCase() : ""
            textFormat: Text.PlainText
            color: root.fg
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.bold: true
            font.letterSpacing: 0.9
          }
        }

        Rectangle {
          visible: root.event && root.event.pad_label
          radius: height / 2
          color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.08)
          border.width: 1
          border.color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.28)
          implicitWidth: padBadge.implicitWidth + Style.space(14)
          implicitHeight: padBadge.implicitHeight + Style.space(6)

          Text {
            id: padBadge
            anchors.centerIn: parent
            text: root.event ? (root.event.pad_label || "") : ""
            textFormat: Text.PlainText
            color: root.fg
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.bold: true
            font.letterSpacing: 0.6
          }
        }
      }
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
      font.pixelSize: Style.font.title
      font.bold: true
    }

    Text {
      width: parent.width
      text: root.event ? root.event.rocket : ""
      textFormat: Text.PlainText
      elide: Text.ElideRight
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
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
      text: root.event ? ("Can we see it?  " + (root.event.can_we_see || "")) : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.body
    }

    Text {
      width: parent.width
      visible: root.event && root.event.webcast
      text: "Watch the webcast"
      textFormat: Text.PlainText
      color: root.accent
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      font.underline: watchHit.containsMouse
      font.bold: true

      MouseArea {
        id: watchHit
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        hoverEnabled: true
        onClicked: if (root.event && root.event.webcast) Qt.openUrlExternally(root.event.webcast)
      }
    }
  }
}
