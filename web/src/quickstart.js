// The 10 everyday phrases to record first (help, pain, needs), exactly as in
// data/default_phrases_*.txt (the same meanings in every language). Speak opens once every one
// of them the user has is ready.
export const NEEDED = 3
const QUICK_START = {
  hi: [
    'मदद चाहिए',
    'दर्द हो रहा है',
    'पानी चाहिए',
    'बाथरूम जाना है',
    'दवाई दे दो',
    'डॉक्टर को बुलाओ',
    'सांस लेने में तकलीफ़ है',
    'भूख लगी है',
    'ठंड लग रही है',
    'मुझे उठा दो',
  ],
  en: [
    'I need help',
    "I'm in pain",
    'I need water',
    'I need the bathroom',
    'Give me my medicine',
    'Call the doctor',
    "I can't breathe properly",
    "I'm hungry",
    'I feel cold',
    'Help me sit up',
  ],
  ta: [
    'எனக்கு உதவி வேணும்',
    'வலிக்குது',
    'தண்ணி வேணும்',
    'பாத்ரூம் போகணும்',
    'மருந்து குடுங்க',
    'டாக்டரை கூப்பிடுங்க',
    'மூச்சு விட கஷ்டமா இருக்கு',
    'பசிக்குது',
    'குளிருது',
    'என்னை உட்கார வைங்க',
  ],
  te: [
    'నాకు సహాయం కావాలి',
    'నొప్పిగా ఉంది',
    'నీళ్ళు కావాలి',
    'బాత్రూమ్ కి వెళ్ళాలి',
    'మందులు ఇవ్వండి',
    'డాక్టర్ ని పిలవండి',
    'ఊపిరి ఆడటం లేదు',
    'ఆకలిగా ఉంది',
    'చలిగా ఉంది',
    'నన్ను కూర్చోబెట్టండి',
  ],
  kn: [
    'ನನಗೆ ಸಹಾಯ ಬೇಕು',
    'ನೋವಾಗ್ತಿದೆ',
    'ನೀರು ಬೇಕು',
    'ಬಾತ್ರೂಮ್ ಹೋಗಬೇಕು',
    'ಔಷಧಿ ಕೊಡಿ',
    'ಡಾಕ್ಟರನ್ನು ಕರೀರಿ',
    'ಉಸಿರಾಡೋಕೆ ಕಷ್ಟ ಆಗ್ತಿದೆ',
    'ಹಸಿವಾಗ್ತಿದೆ',
    'ಚಳಿ ಆಗ್ತಿದೆ',
    'ನನ್ನನ್ನು ಎಬ್ಬಿಸಿ ಕೂರಿಸಿ',
  ],
  ml: [
    'എനിക്ക് സഹായം വേണം',
    'വേദനിക്കുന്നു',
    'വെള്ളം വേണം',
    'ബാത്ത്റൂമിൽ പോകണം',
    'മരുന്ന് തരൂ',
    'ഡോക്ടറെ വിളിക്കൂ',
    'ശ്വാസം മുട്ടുന്നു',
    'വിശക്കുന്നു',
    'തണുക്കുന്നു',
    'എന്നെ എഴുന്നേൽപ്പിച്ച് ഇരുത്തൂ',
  ],
  mr: [
    'मला मदत हवी आहे',
    'दुखतंय',
    'पाणी हवं',
    'बाथरूमला जायचंय',
    'औषध द्या',
    'डॉक्टरांना बोलवा',
    'श्वास घ्यायला त्रास होतोय',
    'भूक लागलीय',
    'थंडी वाजतेय',
    'मला उठवून बसवा',
  ],
  gu: [
    'મને મદદ જોઈએ છે',
    'દુખે છે',
    'પાણી જોઈએ છે',
    'બાથરૂમ જવું છે',
    'દવા આપો',
    'ડૉક્ટરને બોલાવો',
    'શ્વાસ લેવામાં તકલીફ થાય છે',
    'ભૂખ લાગી છે',
    'ઠંડી લાગે છે',
    'મને બેઠા કરો',
  ],
  bn: [
    'আমার সাহায্য দরকার',
    'ব্যথা করছে',
    'জল চাই',
    'বাথরুমে যাব',
    'ওষুধটা দাও',
    'ডাক্তার ডাকো',
    'শ্বাস নিতে কষ্ট হচ্ছে',
    'খিদে পেয়েছে',
    'ঠান্ডা লাগছে',
    'আমাকে তুলে বসাও',
  ],
  pa: [
    'ਮੈਨੂੰ ਮਦਦ ਚਾਹੀਦੀ ਹੈ',
    'ਦਰਦ ਹੋ ਰਿਹਾ ਹੈ',
    'ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ',
    'ਬਾਥਰੂਮ ਜਾਣਾ ਹੈ',
    'ਦਵਾਈ ਦੇ ਦਿਓ',
    'ਡਾਕਟਰ ਨੂੰ ਬੁਲਾਓ',
    'ਸਾਹ ਲੈਣ ਵਿੱਚ ਤਕਲੀਫ਼ ਹੈ',
    'ਭੁੱਖ ਲੱਗੀ ਹੈ',
    'ਠੰਢ ਲੱਗ ਰਹੀ ਹੈ',
    'ਮੈਨੂੰ ਉਠਾ ਦਿਓ',
  ],
}

// sample_count counts recordings in the language the user speaks now, the only ones Sunn
// matches against; a phrase recorded only in another language has 0 and needs recording again.
export const ready = (phrase) => phrase.sample_count >= NEEDED
export const needsRerecord = (phrase) => phrase.sample_count === 0 && phrase.enrolled > 0

// The starter phrase for "I need water" in a language, for trying a voice.
export const waterPhrase = (language) => (QUICK_START[language] || QUICK_START.hi)[2]

// The user's quick-start phrases, in that order: the ones they still have.
export function quickStart(phrases, language) {
  return (QUICK_START[language] || []).map((text) => phrases.find((p) => p.text === text)).filter(Boolean)
}

// Returns user-selectable goal targets adapted dynamically to totalAvailable.
export function getGoalOptions(totalAvailable) {
  if (!totalAvailable || totalAvailable <= 0) return [10]
  const steps = [10, 20, 30]
  const options = []
  for (const s of steps) {
    if (s < totalAvailable) {
      options.push(s)
    }
  }
  if (!options.includes(totalAvailable)) {
    options.push(totalAvailable)
  }
  return options
}

// Ordered phrases up to the target goal, keeping starter phrases first.
export function getTargetPhrases(phrases, language, goal = 10) {
  if (!Array.isArray(phrases) || !phrases.length) return []
  const starter = quickStart(phrases, language)
  const others = phrases.filter((p) => !starter.includes(p))
  const fullOrder = [...starter, ...others]
  const effectiveGoal = Math.max(1, Math.min(goal || 10, fullOrder.length))
  return fullOrder.slice(0, effectiveGoal)
}

// Central calculation for preparation progress toward the chosen goal.
// Speak opens once every phrase in the target goal is ready.
export function speakProgress(phrases, language, userGoal = 10) {
  if (!Array.isArray(phrases) || !phrases.length) {
    const fallbackGoal = userGoal || 10
    return {
      ready: 0,
      total: fallbackGoal,
      open: false,
      available: 0,
      goal: fallbackGoal,
      targetPhrases: [],
      nextPhrase: null,
      totalDone: 0,
      percent: 0,
    }
  }

  const starter = quickStart(phrases, language)
  const others = phrases.filter((p) => !starter.includes(p))
  const fullOrder = [...starter, ...others]
  const totalAvailable = fullOrder.length

  if (!starter.length && totalAvailable === 0) {
    return {
      ready: 0,
      total: 1,
      open: false,
      available: 0,
      goal: 1,
      targetPhrases: [],
      nextPhrase: null,
      totalDone: 0,
      percent: 0,
    }
  }

  const effectiveGoal = Math.max(1, Math.min(userGoal || 10, totalAvailable))
  const targetPhrases = fullOrder.slice(0, effectiveGoal)

  const done = targetPhrases.filter(ready).length
  const totalDone = fullOrder.filter(ready).length
  const nextPhrase = targetPhrases.find((p) => !ready(p)) || fullOrder.find((p) => !ready(p)) || null

  return {
    ready: done,
    total: effectiveGoal,
    open: done >= effectiveGoal,
    available: totalAvailable,
    goal: effectiveGoal,
    targetPhrases,
    nextPhrase,
    totalDone,
    percent: Math.round((done / effectiveGoal) * 100),
  }
}
