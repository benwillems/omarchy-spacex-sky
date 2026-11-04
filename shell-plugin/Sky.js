.pragma library

function pad(n) {
  return (n < 10 ? "0" : "") + n
}

function remaining(epoch, nowMs) {
  if (!epoch) return null
  return Math.floor(epoch - nowMs / 1000)
}

function coarse(epoch, nowMs) {
  var secs = remaining(epoch, nowMs)
  if (secs === null) return ""
  if (secs < 0) return "now"
  var d = Math.floor(secs / 86400)
  var h = Math.floor((secs % 86400) / 3600)
  var m = Math.floor((secs % 3600) / 60)
  if (d > 0) return d + "d " + h + "h"
  if (h > 0) return h + "h " + pad(m) + "m"
  return m + "m"
}

function countdown(epoch, nowMs, timeSet) {
  if (timeSet === false) return "date only"
  var secs = remaining(epoch, nowMs)
  if (secs === null) return ""
  if (secs < -3600) return "passed"
  if (secs < 0) return "now"
  var d = Math.floor(secs / 86400)
  var h = Math.floor((secs % 86400) / 3600)
  var m = Math.floor((secs % 3600) / 60)
  var s = secs % 60
  if (d > 0) return d + "d " + h + "h " + pad(m) + "m"
  if (h > 0) return h + "h " + pad(m) + "m " + pad(s) + "s"
  return m + "m " + pad(s) + "s"
}

function lead(epoch, nowMs, timeSet) {
  var text = countdown(epoch, nowMs, timeSet)
  if (!text || text === "passed" || text === "date only") return text
  if (text === "now") return "up now"
  return "in  " + text
}

function barWhen(epoch, timeSet, fallback, nowMs) {
  if (timeSet === false) return fallback || ""
  return coarse(epoch, nowMs)
}

function barText(board, nowMs) {
  var bar = board && board.bar
  if (!bar) return "🚀"
  var parts = []
  if (bar.hero_kind === "train" && bar.hero_end_epoch && bar.hero_end_epoch * 1000 > nowMs && bar.train_clock) {
    parts.push("★ " + bar.train_clock)
  } else if (bar.hero_kind === "launch" && bar.hero_epoch) {
    var when = barWhen(bar.hero_epoch, bar.hero_time_set, bar.hero_when, nowMs)
    var place = bar.hero_label || "Launch"
    parts.push(("🚀 " + place + (when ? (" " + when) : "")).trim())
  }
  var otherFlorida = bar.florida_epoch && bar.florida_uid && bar.florida_uid !== bar.hero_uid
  if (otherFlorida && (bar.hero_kind !== "launch" || !bar.hero_florida)) {
    var flWhen = barWhen(bar.florida_epoch, bar.florida_time_set, bar.florida_when, nowMs)
    var flPlace = bar.florida_label || "FL"
    parts.push(("🚀 " + flPlace + (flWhen ? (" " + flWhen) : "")).trim())
  }
  return parts.length ? parts.join("  ") : "🚀"
}
