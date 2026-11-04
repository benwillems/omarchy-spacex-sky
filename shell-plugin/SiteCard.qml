import QtQuick
import qs.Commons
import qs.Ui

// One city. Pads in that city share this star.
Rectangle {
  id: root

  property var site: null
  property bool selected: false

  signal favoriteToggled(string siteId)
  signal filterRequested(string siteId)

  readonly property bool fav: site && site.favorite === true
  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  implicitWidth: Style.space(148)
  implicitHeight: Math.max(body.implicitHeight + Style.space(20), Style.space(108))
  radius: Math.max(Style.cornerRadius, 14)
  color: fav ? Qt.rgba(accent.r, accent.g, accent.b, 0.18)
             : Qt.rgba(fg.r, fg.g, fg.b, 0.045)
  border.width: (fav || selected) ? 2 : 1
  border.color: fav ? Qt.rgba(accent.r, accent.g, accent.b, 0.95)
                    : (selected ? Qt.rgba(fg.r, fg.g, fg.b, 0.7)
                                : Qt.rgba(fg.r, fg.g, fg.b, 0.16))

  Column {
    id: body
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(10)
    spacing: Style.space(2)

    Row {
      width: parent.width
      spacing: Style.space(6)

      Text {
        id: starMark
        text: root.fav ? "★" : "☆"
        color: root.fav ? root.accent : root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.heading

        MouseArea {
          id: starHit
          anchors.fill: parent
          anchors.margins: -8
          cursorShape: Qt.PointingHandCursor
          onClicked: if (root.site) root.favoriteToggled(root.site.id)

          PanelToolTip {
            visible: starHit.containsMouse
            text: {
              if (!root.site) return ""
              var name = root.site.name || root.site.short || ""
              return root.fav ? ("Stop alerts for " + name) : ("Alert me for " + name)
            }
            fontFamily: Style.font.family
          }
        }
      }

      Text {
        width: Math.max(Style.space(48), parent.width - Style.space(28))
        text: root.site ? (root.site.label || root.site.short) : ""
        textFormat: Text.PlainText
        elide: Text.ElideRight
        color: root.fg
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.bold: true
      }
    }

    Text {
      width: parent.width
      visible: root.site && root.site.detail
      text: root.site ? (root.site.detail || "") : ""
      textFormat: Text.PlainText
      elide: Text.ElideRight
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }

    Text {
      width: parent.width
      text: root.site ? (root.site.region_name || "").toUpperCase() : ""
      textFormat: Text.PlainText
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 1.1
    }

    Text {
      width: parent.width
      text: {
        if (!root.site) return ""
        if (root.site.next_when) return root.site.next_when
        return "No launch listed"
      }
      textFormat: Text.PlainText
      elide: Text.ElideRight
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }

  MouseArea {
    id: hit
    anchors.fill: parent
    cursorShape: Qt.PointingHandCursor
    z: -1
    onClicked: if (root.site) root.filterRequested(root.site.id)

    PanelToolTip {
      visible: hit.containsMouse
      text: {
        if (!root.site) return ""
        var name = root.site.name || root.site.short || "this city"
        return root.selected ? ("Show all launches") : ("Show launches from " + name)
      }
      fontFamily: Style.font.family
    }
  }
}
