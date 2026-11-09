const html = require('choo/html')

const Video = (state, emit) => {
  return html`
    ${VideoControls(state, emit)}
    ${VideoPlayer(state, emit)}
  `
}

const VideoControls = (state, emit) => {
  const onsubmit = (e) => {
    e.preventDefault()
    return false
  }
  return html`
    <form class="video-controls" onsubmit=${onsubmit}>
      <input type="text" name="videoUrl" />
      <button onclick=${() => emit('loadVideo')}>Load video</button>
      ${state.videoError}
    </form>
  `
}
const VideoPlayer = (state, emit) => {
  if (state.videoId) {
    return html`
    <div class="video-player">
      <iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/${state.videoId}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
    `
  } else {
    return html`
      <div class="video-player"></div>
    `
  }
}

module.exports = Video
