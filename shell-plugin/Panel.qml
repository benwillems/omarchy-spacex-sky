import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Sky.js" as Sky

Panel {
  id: root
  moduleName: "bjw.spacex-sky"
  ipcTarget: "bjw.spacex-sky"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root

  readonly property string bin: {
    var home = Quickshell.env("HOME") || ""
    return (home ? home : "/home/bjw") + "/.local/bin/spacex-sky"
  }
  readonly property color fg: Color.popups.text
  readonly property color accent: Color.accent
  readonly property color muted: Qt.rgba(fg.r, fg.g, fg.b, 0.62)

  property var board: ({})
  property string pendingFilter: ""
  property string loadError: ""
  property bool refreshQueued: false
  property var mutateQueued: []
  property double nowMs: Date.now()

  readonly property var heroEvent: board && board.hero ? board.hero : null
  readonly property var launchCards: board && board.launches ? board.launches : []
  readonly property var trainCards: board && board.trains ? board.trains : []
  readonly property var tonightTrains: board && board.trains_tonight ? board.trains_tonight : []
  readonly property var laterTrains: board && board.trains_later ? board.trains_later : []
  readonly property var chips: board && board.chips ? board.chips : []
  readonly property var sites: board && board.sites ? board.sites : []
  readonly property bool fetching: fetchProc.running
  readonly property var floridaAlert: {
    var card = board && board.florida ? board.florida : null
    if (!card || !card.epoch) return null
    if (heroEvent && heroEvent.uid === card.uid) return null
    if (filterId !== "all") return null
    return card
  }
  readonly property string filterId: pendingFilter !== "" ? pendingFilter : (board && board.filter ? board.filter : "all")
  readonly property string placeName: board && board.place ? board.place : "Jacksonville"
  readonly property bool ready: !!(board && board.generated_epoch)
  readonly property string barText: Sky.barText(board, nowMs)
  readonly property string barTip: (board && board.bar && board.bar.tooltip) ? board.bar.tooltip : "SpaceX sky\nClick to open the sky board"
  readonly property bool showTrains: !!(heroEvent && heroEvent.kind === "train") || tonightTrains.length > 0 || laterTrains.length > 0

  function setCenterHoverRevealSuppressed(value) {
    if (root.bar && typeof root.bar.setCenterHoverRevealSuppressed === "function")
      root.bar.setCenterHoverRevealSuppressed(value)
    else if (root.bar && "centerHoverRevealSuppressed" in root.bar)
      root.bar.centerHoverRevealSuppressed = value
  }

  function open() {
    setCenterHoverRevealSuppressed(false)
    root.controller.show()
    root.maybeRefresh()
  }

  function openFromHotkey() {
    root.controller.show()
    root.maybeRefresh()
    Qt.callLater(function() {
      if (root.opened) setCenterHoverRevealSuppressed(true)
    })
  }

  function close() {
    setCenterHoverRevealSuppressed(false)
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.openFromHotkey()
  }

  function maybeRefresh() {
    var stamp = board && board.generated_epoch ? board.generated_epoch : 0
    if (!stamp || (Date.now() / 1000 - stamp) > 45) refresh()
  }

  function refresh() {
    if (fetchProc.running) {
      refreshQueued = true
      return
    }
    refreshQueued = false
    fetchProc.command = [bin, "json"]
    fetchProc.running = true
  }

  function runMutate(args) {
    var cmd = [bin]
    for (var i = 0; i < args.length; i++) cmd.push(String(args[i]))
    if (mutateProc.running) {
      mutateQueued = cmd
      return
    }
    mutateProc.command = cmd
    mutateProc.running = true
  }

  function chooseFilter(id) {
    if (!id || id === filterId) return
    pendingFilter = id
    runMutate(["filter", "set", id])
  }

  function chooseCity(id) {
    if (!id) return
    if (id === filterId) chooseFilter("all")
    else chooseFilter(id)
  }

  function toggleFavorite(siteId) {
    if (!siteId) return
    flipFavorite(siteId)
    runMutate(["favorite", "toggle", siteId])
  }

  function flipFavorite(siteId) {
    if (!board || !board.generated_epoch) return
    var copy = JSON.parse(JSON.stringify(board))
    var fav = copy.favorites ? copy.favorites.slice() : []
    var has = fav.indexOf(siteId) >= 0
    copy.favorites = has ? fav.filter(function(item) { return item !== siteId }) : fav.concat([siteId])
    function mark(card) {
      if (card && (card.site_id === siteId || card.city_id === siteId)) card.favorite = !has
    }
    mark(copy.hero)
    mark(copy.florida)
    var list = copy.launches || []
    for (var i = 0; i < list.length; i++) mark(list[i])
    var siteList = copy.sites || []
    for (var s = 0; s < siteList.length; s++) {
      if (siteList[s] && siteList[s].id === siteId) siteList[s].favorite = !has
    }
    board = copy
  }

  onBoardChanged: {
    if (pendingFilter !== "" && board && board.filter === pendingFilter)
      pendingFilter = ""
  }

  Component.onCompleted: refresh()

  Timer {
    interval: 1000
    running: root.opened
    repeat: true
    onTriggered: root.nowMs = Date.now()
  }

  Timer {
    interval: 30000
    running: !root.opened
    repeat: true
    onTriggered: root.nowMs = Date.now()
  }

  Timer {
    interval: 60000
    running: true
    repeat: true
    onTriggered: root.refresh()
  }

  Process {
    id: fetchProc
    stdout: StdioCollector {
      id: fetchOut
      waitForEnd: true
      onStreamFinished: {
        var raw = String(text || "").trim()
        if (!raw) {
          root.loadError = String(fetchErr.text || "The sky board did not answer.").trim()
          return
        }
        try {
          root.board = JSON.parse(raw)
          root.loadError = ""
        } catch (e) {
          root.loadError = "Could not read the sky board."
        }
      }
    }
    stderr: StdioCollector { id: fetchErr }
    onExited: if (root.refreshQueued) root.refresh()
  }

  Process {
    id: mutateProc
    onExited: {
      if (root.mutateQueued && root.mutateQueued.length) {
        var cmd = root.mutateQueued
        root.mutateQueued = []
        mutateProc.command = cmd
        mutateProc.running = true
        return
      }
      root.refresh()
    }
  }

  SkyPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(600))
    contentHeight: panel.fittedContentHeight(Math.min(Math.max(column.implicitHeight, Style.space(240)), Style.space(820)))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onMoveRequested: function(dx, dy) {
        if (dy === 0) return
        var maxY = Math.max(0, flick.contentHeight - flick.height)
        flick.contentY = Math.max(0, Math.min(maxY, flick.contentY + dy * 72))
      }

      Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        interactive: contentHeight > height + 1

        Column {
          id: column
          width: flick.width
          spacing: Style.space(12)

          Item {
            width: parent.width
            height: Math.max(placeLine.implicitHeight, refreshHit.implicitHeight)

            Text {
              id: placeLine
              anchors.left: parent.left
              anchors.right: refreshHit.left
              anchors.rightMargin: Style.space(8)
              anchors.verticalCenter: parent.verticalCenter
              text: root.ready
                    ? ("From " + root.placeName + "  ·  times in " + (root.board.tz_label || "ET"))
                    : (root.loadError !== "" ? root.loadError : "Looking up the sky…")
              textFormat: Text.PlainText
              elide: Text.ElideRight
              color: root.loadError !== "" && !root.ready ? Color.urgent : root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.bodySmall
            }

            Text {
              id: refreshHit
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              text: root.fetching ? "Updating…" : "Refresh"
              textFormat: Text.PlainText
              color: root.accent
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.bold: true
              font.underline: refreshMouse.containsMouse && !root.fetching
              opacity: root.fetching ? 0.7 : 1

              MouseArea {
                id: refreshMouse
                anchors.fill: parent
                anchors.margins: -6
                enabled: !root.fetching
                cursorShape: Qt.PointingHandCursor
                hoverEnabled: true
                onClicked: root.refresh()
              }
            }
          }

          HeroCard {
            width: parent.width
            visible: root.heroEvent !== null
            event: root.heroEvent
            nowMs: root.nowMs
            place: root.placeName
          }

          EmptyNote {
            message: root.heroEvent ? "" : (root.ready ? (root.board.empty_hero || "Nothing coming up.") : "")
          }

          FloridaAlert {
            width: parent.width
            visible: root.floridaAlert !== null
            event: root.floridaAlert
            nowMs: root.nowMs
          }

          PanelSectionHeader {
            text: "CITIES"
            foreground: root.fg
            fontFamily: Style.font.family
            visible: root.sites.length > 0
          }

          Text {
            width: parent.width
            visible: root.sites.length > 0
            text: "Tap a city to see its launches. The star turns on alerts."
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }

          Flow {
            id: siteFlow
            width: parent.width
            spacing: Style.space(8)
            visible: root.sites.length > 0

            Repeater {
              model: root.sites

              delegate: SiteCard {
                required property var modelData
                site: modelData
                selected: modelData.id === root.filterId
                width: Math.floor((siteFlow.width - siteFlow.spacing * 2) / 3)
                onFavoriteToggled: function(siteId) { root.toggleFavorite(siteId) }
                onFilterRequested: function(siteId) { root.chooseCity(siteId) }
              }
            }
          }

          Flickable {
            id: chipFlick
            width: parent.width
            height: chipRow.implicitHeight
            contentWidth: chipRow.implicitWidth
            contentHeight: height
            clip: true
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width
            visible: root.chips.length > 1 || (root.filterId !== "all" && root.filterId !== "favorites")

            Row {
              id: chipRow
              spacing: Style.space(6)

              Repeater {
                model: root.chips

                delegate: Rectangle {
                  id: chip
                  required property var modelData
                  readonly property bool on: modelData.id === root.filterId
                  implicitWidth: chipLabel.implicitWidth + Style.space(22)
                  implicitHeight: Style.space(30)
                  radius: height / 2
                  color: on ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.22) : Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.06)
                  border.width: 1
                  border.color: on ? root.accent : Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.16)

                  Text {
                    id: chipLabel
                    anchors.centerIn: parent
                    text: modelData.label
                    textFormat: Text.PlainText
                    color: chip.on ? root.accent : root.fg
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    font.bold: chip.on
                  }

                  MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.chooseFilter(modelData.id)
                  }
                }
              }
            }
          }

          PanelSectionHeader {
            text: "NEXT LAUNCHES"
            foreground: root.fg
            fontFamily: Style.font.family
            visible: root.ready
          }

          Repeater {
            model: root.launchCards

            delegate: LaunchCard {
              required property var modelData
              width: column.width
              event: modelData
              nowMs: root.nowMs
            }
          }

          EmptyNote {
            message: root.ready && root.launchCards.length === 0 ? (root.board.empty_launches || "") : ""
          }

          PanelSectionHeader {
            text: "TONIGHT"
            foreground: root.fg
            fontFamily: Style.font.family
            visible: root.ready && root.tonightTrains.length > 0
          }

          Repeater {
            model: root.tonightTrains

            delegate: TrainCard {
              required property var modelData
              width: column.width
              event: modelData
              nowMs: root.nowMs
            }
          }

          PanelSectionHeader {
            text: "LATER TRAINS"
            foreground: root.fg
            fontFamily: Style.font.family
            visible: root.ready && root.laterTrains.length > 0
          }

          Repeater {
            model: root.laterTrains

            delegate: TrainCard {
              required property var modelData
              width: column.width
              event: modelData
              nowMs: root.nowMs
            }
          }

          EmptyNote {
            message: root.ready && !root.showTrains ? (root.board.empty_trains || "") : ""
          }

          Text {
            width: parent.width
            visible: root.showTrains
            text: root.board.train_fine_print || ""
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }

          Text {
            width: parent.width
            visible: !!(root.board && root.board.errors && root.board.errors.length > 0)
            text: root.board && root.board.errors ? root.board.errors.join("\n") : ""
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: Color.urgent
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }
        }
      }
    }
  }
}
