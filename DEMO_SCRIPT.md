# Sehat Saathi — screen-recording walkthrough (about 3 minutes)

One narrator, screen recording only. App in English, narration in English; only the spoken complaint is in Hindi. Each step: what to do on screen, then what to say.

Before recording: run `make demo-reset` so the visit list is empty, open the app in Chrome's phone-size view, log in (9000000001 / 1234), tap **English** in the language switch at the top right (the choice is remembered) and allow the microphone.

---

**1. Home**
- Do: Nothing; the home screen is showing.
- Say: "This is Sehat Saathi, a web app for ASHA workers. It turns what a family describes during a home visit into an urgency level, a referral plan and information on government schemes. The red danger-sign button stays at the top of every screen. For this demo we have built one complete pathway, cough in an adult, which covers TB screening, together with the danger-sign check and scheme information."

**2. New visit**
- Do: Tap **Start visit**. Fill in Ramesh Kumar, 45, Male, Rampur. Tap **Start visit for this person**.
- Say: "I'll start a visit for a sample person."

**3. Voice input**
- Do: Tap **Yes, record**, then the mic button. Speak: **"मुझे दो हफ्ते से खासी है और बुखार भी है, रात को पसीना आता है। इलाज के लिए पैसे नहीं हैं।"** Tap **Stop**, then **Continue to questions**.
- Say: "Recording only starts after consent is recorded. Families speak Hindi, so I'll describe a sample complaint in Hindi; the screens themselves can be in Hindi or English. The speech is transcribed by AI4Bharat's IndicConformer model, which we run on our own GPU server."

**4. Suggested facts**
- Do: Pause on the screen. Then tap **Continue to questions**.
- Say: "A locally hosted language model, Qwen 2.5 7B, extracts facts from the transcript: cough for 14 days, fever and night sweats. Each one is linked to the highlighted words it came from. Durations like 'two weeks' are converted by code, not by the model. These are suggestions only and can be removed."

**5. Questions**
- Do: Answer **No** to every question except the fever duration: tap **1 week**, then **Next**.
- Say: "The app now asks only for what is still missing, starting with warning signs. It doesn't ask a generic checklist: every question is there because a rule in the cough pathway needs that answer, and every rule is taken from an official Government of India document. For cough these are the National TB Elimination Programme's National Guidance on Differentiated TB Care from 2025, which gives the red-flag signs for immediate referral, the NTEP training modules, which define presumptive TB, the TB Mukt Bharat Abhiyaan 2026 campaign document for high-risk groups, and the NHM's ASHA module on non-communicable diseases. Durations can be entered with one tap."

**6. Confirmation**
- Do: Scroll through the list. Tick **I have checked these with the family**, then tap **Confirm and see the result**.
- Say: "Before any result, the worker reviews and confirms every fact."

**7. Result**
- Do: Pause on **See a doctor soon**. Tap **Why?** to open it.
- Say: "The urgency comes from a deterministic rules engine, not from the AI. The rules are taken from the national TB programme guidelines, and this panel shows the rule and its source document and page. A cough of two weeks or more means a referral for a TB test. The pathway is marked as draft until clinicians review it."

**8. Referral plan**
- Do: Tap **See the plan**. Play **Read aloud** for a few seconds, then tap **Stop reading**.
- Say: "The plan says where to go and by when: the Primary Health Centre, within 24 hours. The instructions for the family can be read aloud, in Hindi or English depending on the visit language, and a referral note for the doctor can be printed or shared."

**9. Scheme information**
- Do: Tap **Support information**.
- Say: "Because a TB test is needed and a money concern was mentioned, the app shows relevant government schemes: free TB testing and treatment, and Ni-kshay Poshan Yojana. They are shown as 'may help' or 'needs checking'. Nothing is promised as an entitlement."

**10. Danger signs**
- Do: Tap **Danger signs**, then **Unconscious or not responding to voice or touch**.
- Say: "Finally, the danger-sign check. Selecting a sign immediately shows emergency instructions and the 108 ambulance number, without needing the AI or the network. These signs come from the NHSRC's emergency care training for frontline workers."

**11. What's next** (stay on any screen, or go back to the home screen)
- Say: "That's what we have so far: one pathway, Hindi speech, and urgency decided only by rules with cited sources. Next, we plan to add more pathways the same way, starting with pregnancy check-ups based on the Mother and Child Protection card and a sick child based on the IMNCI chart booklet; we already have those documents and schemes such as JSY, JSSK and PMMVY in our knowledge base. We also plan to support English and mixed Hindi-English speech, and to get the pathways reviewed by clinicians so the draft label can be removed. To sum up: AI handles the listening, rules decide urgency, and the health worker confirms everything."

---

If speech comes out wrong, type the same sentence into the text box instead. If the model takes more than 6 seconds, tap **Do it by hand**. Either way the rest of the flow is the same.
