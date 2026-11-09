let stopWords = require('./stop_words_nltk.json')

function getDefaultStopWords() {
  return stopWords.map(w => w.toUpperCase())
}

function getSavedStopWords() {
  try {
    let savedStopWords = JSON.parse(localStorage.getItem('stopWords')) || []
    return savedStopWords.map(w => w.toUpperCase())
  } catch (e) {
    console.log(e)
    return []
  }
}

module.exports = (state, emitter) => {
  state.videoUrl = null
  state.videoId = null
  state.videoError = null

  let defaultWords = getDefaultStopWords()
  let savedWords = getSavedStopWords()
  state.stopWords = savedWords.concat(defaultWords)

  state.wordInput = ''
  state.minCount = 2
  state.text = ``
  state.interim_transcript = ''
  state.words = processWords(state)

  state.recognitionError = null
  state.recognizing = false
  if (window.webkitSpeechRecognition) {
    setupRecognition(state, emitter)
  } else {
    state.recognitionError = "This website only works on Google Chrome :("
  }

  state.settingsOpened = true

  emitter.on('loadVideo', () => {
    let input = document.querySelector('.video-controls input[name="videoUrl"]')
    let value = input ? input.value : ''
    try {
      let url = new URL(value)
      state.videoId = url.searchParams.get('v')
      state.videoError = null
    } catch (e) {
      state.videoError = 'Invalid url'
    }
    emitter.emit('render')
  })

  emitter.on('removeStopWord', (i) => {
    state.stopWords.splice(i, 1)
    localStorage.setItem('stopWords', JSON.stringify(state.stopWords))
    emitter.emit('render')
  })
  emitter.on('addStopWord', () => {
    let input = document.querySelector('#word-form input[name="word"]')
    if (input && input.value !== '') {
      let words = input.value.split(',').map(w => w.trim().toUpperCase())
      state.stopWords = words.concat(state.stopWords)
    }
    localStorage.setItem('stopWords', JSON.stringify(state.stopWords))
    emitter.emit('render')
  })
  emitter.on('resetStopWords', () => {
    localStorage.setItem('stopWords', null)
    state.stopWords = getDefaultStopWords()
    emitter.emit('render')
  })

  emitter.on('startRecognition', () => {
    state.recognizing = true
    state.recognition.start()
    emitter.emit('render')
  })
  emitter.on('stopRecognition', () => {
    state.recognizing = false
    state.recognition.stop()
    emitter.emit('render')
  })

  emitter.on('showSettings', () => {
    state.settingsOpened = true
    emitter.emit('render')
  })
  emitter.on('hideSettings', () => {
    state.settingsOpened = false
    emitter.emit('render')
  })

}

function processWords(state) {
  let words = state.text + state.interim_transcript
  words = words.replaceAll('.', '')
  words = words.replaceAll(',', '')
  words = words.replaceAll(',', '')
  words = words.split(' ')
  return words.reduce(function(acc, word) {
    let w = word.toUpperCase()
    if (acc[w]) {
      acc[w] += 1
    } else {
      acc[w] = 1
    }
    return acc
  }, {})
}

function setupRecognition(state, emitter) {
  state.recognition = new webkitSpeechRecognition()
  state.recognition.continuous = true
  state.recognition.interimResults = true
  state.recognition.onstart = function() {
    state.recognizing = true
    emitter.emit('render')
  }
  state.recognition.onend = function() {
    if (state.recognizing) {
      state.recognition.start()
    }
    emitter.emit('render')
  }
  state.recognition.onresult = function(event) {
    state.interim_transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        state.text += event.results[i][0].transcript;
      } else {
        state.interim_transcript += event.results[i][0].transcript;
      }
    }

    state.words = processWords(state)
    state.recognitionError = null
    emitter.emit('render')
  }
  state.recognition.onerror = function(event) {
    state.recognizing = false
    if (event.error == 'no-speech') {
      state.recognitionError = 'no_speech'
    }
    if (event.error == 'audio-capture') {
      state.recognitionError = 'no_microphone'
    }
    if (event.error == 'not-allowed') {
      if (event.timeStamp - state.start_timestamp < 100) {
        state.recognitionError = 'blocked'
      } else {
        state.recognitionError = 'denied'
      }
    }
  }
}
