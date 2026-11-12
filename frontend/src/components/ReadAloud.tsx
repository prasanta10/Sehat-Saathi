import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

/** Browser speech synthesis. Says so plainly when the device has no voice for the language. */
export function ReadAloud({ text, lang }: { text: string; lang: string }) {
  const { t } = useTranslation()
  const [speaking, setSpeaking] = useState(false)
  const [noVoice, setNoVoice] = useState(false)
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined
  useEffect(() => () => synth?.cancel(), [synth])

  function play() {
    if (!synth) return setNoVoice(true)
    if (speaking) {
      synth.cancel()
      return setSpeaking(false)
    }
    const voice = synth.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang))
    if (!voice && lang === 'hi') setNoVoice(true)
    const u = new SpeechSynthesisUtterance(text)
    u.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'
    if (voice) u.voice = voice
    u.rate = 0.9
    u.onend = () => setSpeaking(false)
    setSpeaking(true)
    synth.speak(u)
  }

  return (
    <div className="flex flex-col gap-1">
      <button type="button" data-testid="read-aloud" onClick={play} className="min-h-12 rounded-xl border-2 border-brand px-4 font-bold text-brand">
        <span aria-hidden="true">🔊 </span>
        {speaking ? t('outputs.stop') : t('outputs.play')}
      </button>
      {noVoice && <p role="status">{t('outputs.no_voice')}</p>}
    </div>
  )
}
