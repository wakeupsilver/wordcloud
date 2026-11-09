const html = require('choo/html')

const Transcript = (state, emit) => {
  return html`
    <div class="text">
      <em>Original text:</em>
      ${state.text} ${state.interim_transcript}
    </div>
  `
}

module.exports = Transcript
