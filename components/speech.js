const html = require('choo/html')

const playIcon = require('./icons/media-play.svg')
const stopIcon = require('./icons/media-stop.svg')

const SpeechToText = (state, emit) => {
  let button = null
  if (state.recognition) {
    if (state.recognizing) {
      button = html`
        <button onclick=${() => emit('stopRecognition')}>
          <img src=${stopIcon} alt="stop" />
        </button>
      `
    } else {
      button = html`
        <button onclick=${() => emit('startRecognition')}>
        <img src=${playIcon} alt="start" />
        </button>
      `
    }
  }
  return html`
    <div class="speech-to-text">
      ${button}
      <div>${state.recognitionError || ''}</div>
    </div>
  `
}

module.exports = SpeechToText
