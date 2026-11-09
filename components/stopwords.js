const html = require('choo/html')

const StopWords = (state, emit) => {
  const wordList = state.stopWords.map((word, i) => {
    return html`
      <li>
        ${word}
        <button onclick=${() => emit('removeStopWord', i)}>x</button>
      </li>
    `
  })

  const onsubmit = (e) => {
    e.preventDefault()
    return false
  }

  return html`
    <div class="stop-words">
      <form id="word-form" onsubmit=${onsubmit}>
        <input type="text" name="word">
        <button onclick=${() => emit('addStopWord')}>Add stop word</button>
      </form>
      <ul>
        ${wordList}
      </ul>
      <button onclick=${() => emit('resetStopWords')}>Reset stop words</button>
    </div>
  `
}


module.exports = StopWords;
