import QtQuick
import qs.Commons
import qs.Ui
import "Sky.js" as Sky

// The one thing to pay attention to: what is next, and where.
Rectangle {
  id: root

  property var event: null
  property double nowMs: 0
  property string place: "home"

  signal favoriteToggled(string siteId)

  readonly property bool train: event && event.kind === "train"
  readonly property bool fav: event && event.favorite === true
  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  clip: true
  radius: Math.max(Style.cornerRadius, 16)
  color: fav ? Qt.rgba(accent.r, accent.g, accent.b, 0.16) : Qt.rgba(fg.r, fg.g, fg.b, 0.055)
  border.width: fav ? 2 : 1
  border.color: fav ? accent : Qt.rgba(fg.r, fg.g, fg.b, 0.16)
  implicitHeight: event ? body.implicitHeight + Style.space(36) : Style.space(120)

  Column {
    id: body
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(18)
    spacing: Style.space(8)
    visible: root.event !== null && root.event !== undefined

    Text {
      width: parent.width
      text: (root.train ? "★  NEXT  ·  STARLINK TRAIN" : "🚀  NEXT  ·  " + (root.event ? root.event.kicker : ""))
      textFormat: Text.PlainText
      color: root.fav || root.train ? root.accent : root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 1.1
      elide: Text.ElideRight
    }

    Text {
      width: parent.width
      text: root.event ? root.event.name : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.fontPx(1.7)
      font.bold: true
    }

    Text {
      width: parent.width
      text: {
        if (!root.event) return ""
        var day = root.event.day || ""
        var monthDay = root.event.month_day || ""
        var clock = root.event.clock || ""
        var head = day && monthDay ? (day + ", " + monthDay) : (root.event.date_label || day || monthDay)
        if (head && clock) return head + "  ·  " + clock
        return head || clock
      }
      textFormat: Text.PlainText
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.heading
    }

    Text {
      text: root.event ? Sky.lead(root.event.epoch, root.nowMs, root.event.time_set) : ""
      textFormat: Text.PlainText
      color: root.accent
      font.family: Style.font.family
      font.pixelSize: Style.fontPx(2.15)
      font.bold: true
    }

    Item { width: 1; height: Style.space(4) }

    Text {
      text: {
        if (root.train) return "FROM " + root.place.toUpperCase()
        if (root.event && root.event.pad_label) return "WHERE  ·  " + root.event.pad_label
        return "WHERE"
      }
      textFormat: Text.PlainText
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 1.4
    }

    Row {
      width: parent.width
      spacing: Style.space(12)

      Column {
        width: parent.width - (rose.visible ? rose.width + parent.spacing : 0)
        spacing: 0

        readonly property bool showLook: root.train || (root.event && root.event.visible && root.event.look_dir)

        // Two lines on purpose, so "up" never wraps off the end of the direction.
        Text {
          width: parent.width
          visible: parent.showLook
          text: root.event ? ("Look: " + (root.event.look_dir || root.event.look_words || "")) : ""
          textFormat: Text.PlainText
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.fontPx(2.5)
          font.bold: true
        }

        Text {
          width: parent.width
          visible: root.train && root.event && root.event.look_fists
          text: {
            if (!root.event) return ""
            var fists = root.event.look_fists || ""
            return fists === "right on the horizon" ? fists : (fists + " up")
          }
          textFormat: Text.PlainText
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.fontPx(2.15)
          font.bold: true
        }

        Text {
          width: parent.width
          visible: !root.train
          text: root.event ? root.event.where : ""
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.fg
          font.family: Style.font.family
          font.pixelSize: Style.fontPx(2.35)
          font.bold: true
        }
      }

      Compass {
        id: rose
        visible: root.train || (root.event && root.event.visible && root.event.look_dir)
        size: Style.space(132)
        big: true
        startAz: root.event ? root.event.start_az : 0
        endAz: root.event ? root.event.end_az : 0
        lookAz: root.event ? (root.event.look_az || root.event.start_az) : 0
        ink: root.accent
        ring: root.muted
        muted: root.muted
      }
    }

    Text {
      width: parent.width
      visible: !root.train && root.event && root.event.can_we_see && !(root.event.visible && root.event.look_dir)
      text: root.event ? ("Can we see it?  " + root.event.can_we_see) : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.title
    }

    Text {
      width: parent.width
      visible: !root.train && root.event && root.event.webcast
      text: "Watch the webcast"
      textFormat: Text.PlainText
      color: root.accent
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.underline: heroWatch.containsMouse
      font.bold: true

      MouseArea {
        id: heroWatch
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        hoverEnabled: true
        onClicked: if (root.event && root.event.webcast) Qt.openUrlExternally(root.event.webcast)
      }
    }

    Text {
      width: parent.width
      visible: root.train
      text: root.event
            ? ("Appears " + root.event.start_dir + "  →  " + root.event.end_dir
               + "   ·   peak " + root.event.peak_fists + " (" + root.event.peak_alt + "°)"
               + "   ·   " + root.event.duration)
            : ""
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.fg
      font.family: Style.font.family
      font.pixelSize: Style.font.body
    }

    Text {
      width: parent.width
      text: {
        if (!root.event) return ""
        if (root.train) return root.event.kid_line || ""
        var bits = []
        if (root.event.rocket) bits.push(root.event.rocket)
        if (root.event.pad) bits.push(root.event.pad)
        if (root.event.status) bits.push(root.event.status)
        if (root.event.probability !== null && root.event.probability !== undefined)
          bits.push("weather " + root.event.probability + "%")
        return bits.join("  ·  ")
      }
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
    }

    Text {
      width: parent.width
      visible: text !== ""
      text: {
        if (!root.event) return ""
        if (root.train) return root.event.note || ""
        if (root.event.time_set === false) return "That date is only a placeholder. The exact time is not set yet."
        return root.event.visibility || ""
      }
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }
}
