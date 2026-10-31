"use client";

import Link from "next/link";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
} from "react";

import { motion } from "framer-motion";

import {
  Send,
  Activity,
  ShieldAlert,
  Stethoscope,
  MessageSquare,
  Plus,
  Mic,
  MicOff,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import {
  useUser,
  UserButton,
  SignInButton,
} from "@clerk/nextjs";


export default function Chatbot() {

  const {
    isLoaded,
    isSignedIn,
    user,
  } = useUser();


  const [inputSymptom, setInputSymptom] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  // ============================================================
  // VOICE INPUT
  // ============================================================

  const [isListening, setIsListening] =
    useState(false);

  const [speechLanguage, setSpeechLanguage] =
    useState("en-IN");

  const speechRecognitionRef =
    useRef<any>(null);


  // ============================================================
  // WHAT-IF SYMPTOM SIMULATION
  // ============================================================

  const [whatIfOpen, setWhatIfOpen] =
    useState(false);
  const [conditionsOpen, setConditionsOpen] =
  useState(false);

  const [whatIfSymptom, setWhatIfSymptom] =
    useState("");

  const [whatIfMode, setWhatIfMode] =
    useState<"add" | "remove">("add");

  const [whatIfLoading, setWhatIfLoading] =
    useState(false);

  const [whatIfResult, setWhatIfResult] =
    useState<{
      symptoms: string[];
      prediction: string;
      confidence: number;
    } | null>(null);


  // ============================================================
  // CHAT SESSION STATE
  // ============================================================

  const [currentSessionId, setCurrentSessionId] =
    useState<string | null>(null);

  const [sessionsList, setSessionsList] =
    useState<
      {
        session_id: string;
        preview: string;
      }[]
    >([]);


  // ============================================================
  // DELETE CHAT STATE
  // ============================================================

  const [deletingSessionId, setDeletingSessionId] =
    useState<string | null>(null);

  const longPressTimerRef =
    useRef<ReturnType<typeof setTimeout> | null>(null);


  // ============================================================
  // CHAT MESSAGE TYPE
  // ============================================================

  const [messages, setMessages] =
    useState<
      {
        role: string;
        content: string;

        prediction?: string;

        confidence?: string;

        symptoms?: string[];

        followup_question?: string;

        explanation?: {
          symptom: string;
          contribution: number;
        }[];

        guidance?: {
          do: string[];
          dont: string[];
          monitor: string[];
        };
      }[]
    >([]);


  const messagesEndRef =
    useRef<HTMLDivElement>(null);


  // ============================================================
  // SCROLL
  // ============================================================

  const scrollToBottom = () => {

    setTimeout(() => {

      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
      });

    }, 100);
  };


  useEffect(() => {

    scrollToBottom();

  }, [messages, loading]);


  // ============================================================
  // FETCH ALL PAST CHAT SESSIONS
  // ============================================================

  const fetchSessions = useCallback(() => {

    if (
      isSignedIn &&
      user?.id
    ) {

      fetch(
        `http://127.0.0.1:8000/api/sessions/${user.id}`
      )

        .then((res) => res.json())

        .then((data) => {

          if (data.sessions) {

            setSessionsList(
              data.sessions
            );

          }

        })

        .catch((err) =>
          console.error(
            "Failed to load sessions",
            err
          )
        );
    }

  }, [isSignedIn, user?.id]);


  useEffect(() => {

    fetchSessions();

  }, [fetchSessions]);


  // ============================================================
  // LOAD SPECIFIC CHAT HISTORY
  // ============================================================

  const loadSession = (
    sessionId: string
  ) => {

    setCurrentSessionId(
      sessionId
    );
    fetch(
      `http://127.0.0.1:8000/api/session/${sessionId}`
    )

      .then((res) => res.json())

      .then((data) => {

        if (data.history) {

          setMessages(
            data.history
          );

        }

      })

      .catch((err) =>
        console.error(
          "Failed to load chat history",
          err
        )
      );
  };


  // ============================================================
  // DELETE CHAT
  // ============================================================

  const deleteSession = async (
    sessionId: string
  ) => {

    if (
      !user?.id ||
      deletingSessionId
    ) {
      return;
    }


    const confirmed = window.confirm(
      "Delete this chat history?\n\nThis action cannot be undone."
    );


    if (!confirmed) {
      return;
    }


    setDeletingSessionId(
      sessionId
    );


    try {

      const res = await fetch(
        `http://127.0.0.1:8000/api/session/${sessionId}?user_id=${encodeURIComponent(
          user.id
        )}`,
        {
          method: "DELETE",
        }
      );


      const data =
        await res.json();


      if (!res.ok) {

        throw new Error(
          data.detail ||
          "Failed to delete chat."
        );
      }


      // Remove deleted chat from sidebar

      setSessionsList(
        (previous) =>
          previous.filter(
            (session) =>
              session.session_id !==
              sessionId
          )
      );


      // If currently opened chat was deleted,
      // return to empty chat screen.

      if (
        currentSessionId ===
        sessionId
      ) {

        setCurrentSessionId(
          null
        );

        setMessages([]);

        setWhatIfOpen(false);

        setWhatIfSymptom("");

        setWhatIfResult(null);
      }


    } catch (error) {

      console.error(
        "Delete chat error:",
        error
      );

      alert(
        "Unable to delete this chat. Please try again."
      );

    } finally {

      setDeletingSessionId(
        null
      );

    }
  };


  // ============================================================
  // LONG PRESS HANDLERS
  // ============================================================

  const startLongPress = (
    sessionId: string
  ) => {

    if (longPressTimerRef.current) {

      clearTimeout(
        longPressTimerRef.current
      );

    }


    longPressTimerRef.current =
      setTimeout(() => {

        deleteSession(
          sessionId
        );

      }, 700);
  };


  const cancelLongPress = () => {

    if (
      longPressTimerRef.current
    ) {

      clearTimeout(
        longPressTimerRef.current
      );

      longPressTimerRef.current =
        null;
    }
  };

// ============================================================
// START NEW CHAT
// ============================================================

const startNewChat = () => {
  setCurrentSessionId(null);

  setMessages([]);

  setWhatIfOpen(false);
  setConditionsOpen(false); // Add this line

  setWhatIfSymptom("");

  setWhatIfResult(null);

  setInputSymptom("");
};

  // ============================================================
  // VOICE INPUT
  // ============================================================

  const handleVoiceInput = () => {

    if (isListening) {

      speechRecognitionRef.current?.stop();

      setIsListening(false);

      return;
    }


    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;


    if (!SpeechRecognition) {

      alert(
        "Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge."
      );

      return;
    }


    const recognition =
      new SpeechRecognition();


    recognition.lang =
      speechLanguage;


    recognition.continuous =
      false;


    recognition.interimResults =
      false;


    recognition.maxAlternatives =
      1;


    recognition.onstart = () => {

      setIsListening(
        true
      );

    };


    recognition.onresult = (
      event: any
    ) => {

      const transcript =
        event.results[0][0]
          .transcript;


      setInputSymptom(
        (previous) => {

          if (
            !previous.trim()
          ) {

            return transcript;

          }


          return (
            `${previous} ${transcript}`
          );

        }
      );

    };


    recognition.onerror = (
      event: any
    ) => {

      console.error(
        "Speech recognition error:",
        event.error
      );

      setIsListening(
        false
      );

    };


    recognition.onend = () => {

      setIsListening(
        false
      );

    };


    speechRecognitionRef.current =
      recognition;


    recognition.start();

  };


  // ============================================================
  // SEND MESSAGE
  // ============================================================

  const handleSend = async () => {

    if (
      !inputSymptom.trim() ||
      !isSignedIn ||
        !user?.id
    ) {
      return;
    }


    const newMessages = [

      ...messages,

      {
        role: "user",

        content:
          inputSymptom,
      },

    ];


    setMessages(
      newMessages
    );


    setInputSymptom("");

    setLoading(true);


    try {

      const res = await fetch(
        "http://127.0.0.1:8000/api/chat",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({

            user_id:
              user.id,

            session_id:
              currentSessionId,

            history:
              newMessages,

          }),

        }
      );


      const data =
        await res.json();


      if (
        !res.ok
      ) {

        throw new Error(
          data.detail ||
          "Chat request failed"
        );

      }


      // If this was a new chat,
      // save generated session ID.

      if (
        !currentSessionId &&
        data.session_id
      ) {

        setCurrentSessionId(
          data.session_id
        );

        fetchSessions();

      }


      // Add assistant response.

      setMessages(
        (previous) => [

          ...previous,

          {
            role:
              "assistant",

            content:
              data.reply,

            prediction:
              data.prediction,

            confidence:
              data.confidence,

            symptoms:
              data.symptoms,

            followup_question:
              data.followup_question,

            explanation:
              data.explanation,

            guidance:
              data.guidance,
          },

        ]
      );


    } catch (error) {

      console.error(
        "Error:",
        error
      );


      setMessages(
        (previous) => [

          ...previous,

          {
            role:
              "assistant",

            content:
              "Error connecting to the AI server.",
          },

        ]
      );


    } finally {

      setLoading(false);

    }

  };


  // ============================================================
  // PHASE 8 - WHAT-IF SYMPTOM SIMULATION
  // ============================================================

  const handleWhatIf = async () => {

    if (
      !whatIfSymptom.trim()
    ) {

      return;

    }


    const latestAssistantMessage =
      [...messages]
        .reverse()
        .find(
          (msg) =>
            msg.role ===
              "assistant" &&
            msg.symptoms &&
            msg.symptoms.length >
              0
        );


    if (
      !latestAssistantMessage?.symptoms
    ) {

      return;

    }


    const currentSymptoms =
      latestAssistantMessage.symptoms;


    setWhatIfLoading(
      true
    );


    try {

      const res =
        await fetch(
          "http://127.0.0.1:8000/api/what-if",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({

                current_symptoms:
                  currentSymptoms,

                added_symptoms:
                  whatIfMode === "add"
                    ? [
                        whatIfSymptom
                          .trim()
                          .toLowerCase(),
                      ]
                    : [],

                removed_symptoms:
                  whatIfMode === "remove"
                    ? [
                        whatIfSymptom
                          .trim()
                          .toLowerCase(),
                      ]
                    : [],

              }),

          }
        );


      const data =
        await res.json();


      if (!res.ok) {

        throw new Error(
          data.detail ||
          "What-if request failed"
        );

      }


      setWhatIfResult(
        data
      );


    } catch (error) {

      console.error(
        "What-if simulation error:",
        error
      );


      alert(
        "Unable to run the What-If simulation."
      );


    } finally {

      setWhatIfLoading(
        false
      );

    }

  };


  // ============================================================
  // LOADING INTERFACE
  // ============================================================

  if (!isLoaded) {

    return (

      <div className="h-screen bg-neutral-950 flex items-center justify-center text-white">

        Loading Interface...

      </div>

    );

  }


  // ============================================================
  // MAIN UI
  // ============================================================

  return (

    <div className="fixed inset-0 bg-neutral-950 text-neutral-100 flex overflow-hidden font-sans">


      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <div className="z-20 hidden w-64 flex-col border-r border-white/[0.08] bg-neutral-900/70 backdrop-blur-xl md:flex">


        {/* Logo */}

        <div className="p-4 border-b border-white/10 flex items-center gap-3">

          <div className="p-1.5 bg-blue-500/20 rounded-md border border-blue-500/30">

            <Activity className="w-5 h-5 text-blue-400" />

          </div>


          <h1 className="font-semibold text-sm tracking-wide text-neutral-200">

            ENT Triage AI

          </h1>

        </div>


        {/* Sidebar content */}

        <div className="flex-1 overflow-y-auto p-3 space-y-4">


          {/* New Chat */}

          <button
            onClick={
              startNewChat
            }

           className="flex w-full items-center gap-2 rounded-xl border border-blue-400/20 bg-blue-600/90 px-3 py-2.5 text-sm font-medium text-white shadow-md transition-colors hover:bg-blue-500"
          >

            <Plus className="w-4 h-4" />

            New Chat

          </button>
          {/* Recent Chats */}

          <div className="pt-2 space-y-1">


            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2 px-2 flex items-center gap-2">

              <MessageSquare className="w-3 h-3" />

              Recent Chats

            </p>


            {sessionsList.length === 0 ? (

              <p className="text-xs text-neutral-600 px-2">

                No history yet.

              </p>

            ) : (

              sessionsList.map(
                (session) => (

                  <div
                    key={
                      session.session_id
                    }

                    className="relative"
                  >


                    {/* Chat button */}

                    <button

                     onClick={() =>
                     loadSession(session.session_id)
                    }

                      onPointerDown={() =>
                        startLongPress(
                          session.session_id
                        )
                      }

                      onPointerUp={
                        cancelLongPress
                      }

                      onPointerLeave={
                        cancelLongPress
                      }

                      onPointerCancel={
                        cancelLongPress
                      }

                      onContextMenu={(event) =>
                        event.preventDefault()
                      }

                      disabled={
                        deletingSessionId ===
                        session.session_id
                      }

                      className={`w-full text-left flex flex-col px-3 py-2 pr-9 rounded-lg cursor-pointer transition-colors border select-none ${
                        currentSessionId ===
                        session.session_id

                          ? "bg-white/10 border-white/20 text-white"

                          : "bg-transparent hover:bg-white/5 border-transparent text-neutral-400"
                      } ${
                        deletingSessionId ===
                        session.session_id
                          ? "opacity-50"
                          : ""
                      }`}
                    >

                      <span className="text-sm font-medium truncate w-full">

                        {session.preview}

                      </span>

                    </button>


                    {/* Delete icon */}

                    <button

                      type="button"

                      onClick={(event) => {
                      event.stopPropagation();
                     deleteSession(session.session_id);
                    }}

                      disabled={
                        deletingSessionId ===
                        session.session_id
                      }

                      title="Delete chat"

                      className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-neutral-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >

                      <Trash2 className="w-3.5 h-3.5" />

                    </button>


                  </div>

                )
              )

            )}

          </div>

        </div>


        {/* Profile */}

        <div className="p-4 border-t border-white/10 bg-black/20 flex items-center justify-between">


          {isSignedIn ? (

            <div className="flex items-center gap-3 w-full">

              <UserButton/>

              <span className="text-sm font-medium text-neutral-300 truncate">

                My Profile

              </span>

            </div>

          ) : (

            <SignInButton mode="modal">

              <button className="w-full px-4 py-2 bg-white/10 hover:bg-white/20 text-sm font-medium text-white rounded-lg transition-colors border border-white/10">

                Sign In

              </button>

            </SignInButton>

          )}

        </div>

      </div>


      {/* ======================================================
          MAIN CHAT AREA
      ====================================================== */}

      <div className="flex-1 relative flex flex-col overflow-hidden">


        {/* Background glow */}

        <motion.div

          animate={{
            scale: [1, 1.2, 1],
            opacity: [
              0.15,
              0.3,
              0.15,
            ],
          }}

          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
          }}

          className="absolute top-[10%] left-[20%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px] mix-blend-screen pointer-events-none"
        />


        <motion.div

          animate={{
            scale: [1, 1.3, 1],
            opacity: [
              0.1,
              0.2,
              0.1,
            ],
          }}

          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          }}

          className="absolute bottom-[10%] right-[10%] w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] mix-blend-screen pointer-events-none"
        />


        {/* Mobile header */}

        <div className="md:hidden p-4 border-b border-white/10 flex justify-between items-center bg-neutral-900/50 backdrop-blur-md z-10">


          <div className="flex items-center gap-2">

            <Activity className="w-5 h-5 text-blue-400" />

            <h1 className="font-semibold text-neutral-200">

              ENT Triage AI

            </h1>

          </div>


          {isSignedIn ? (

            <UserButton
              afterSignOutUrl="/"
            />

          ) : (

            <SignInButton mode="modal">

              <button className="text-sm font-medium">

                Sign In

              </button>

            </SignInButton>

          )}

        </div>


        {/* Medical disclaimer */}

        <div className="w-full flex justify-center pt-4 z-10">

          <p className="text-neutral-400 text-xs flex items-center gap-2 bg-black/40 px-4 py-1.5 rounded-full border border-white/5 backdrop-blur-md shadow-lg">

            <ShieldAlert className="w-3 h-3 text-amber-500" />

            AI-powered supportive care. Not a replacement for medical diagnosis.

          </p>

        </div>


        {/* ====================================================
            CHAT CONTENT
        ==================================================== */}

        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth z-10 relative">


          {/* Not signed in */}

          {!isSignedIn ? (

            <div className="h-full flex flex-col items-center justify-center text-neutral-400 space-y-4">

              <SignInButton mode="modal">

                <button className="px-6 py-3 bg-blue-600 text-white rounded-full font-medium hover:bg-blue-500 transition-all shadow-[0_0_15px_rgba(37,99,235,0.4)]">

                  Sign in to Start Triage

                </button>

              </SignInButton>

            </div>


          ) : messages.length === 0 ? (

            /* Empty chat */

            <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
           className="mx-auto flex min-h-full w-full max-w-5xl flex-col justify-center py-8"
>
           {/* Welcome banner */}
            <div className="mb-8 overflow-hidden rounded-3xl border border-teal-400/15 bg-neutral-900/80 p-6 shadow-xl md:p-8">
           <div className="flex items-start justify-between gap-4">
           <div>
           <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-blue-400">
           ENT HEALTH COMPANION
           </p>

           <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl">
           Your health,
           <br />
           understood better.
           </h2>

           <p className="mt-4 max-w-xl text-sm leading-6 text-neutral-400 md:text-base">
            Describe your ear, nose, or throat symptoms and explore
           personalized health-awareness information with AI support.
           </p>

           <button
           type="button"
            onClick={() =>
            setInputSymptom(
              "I would like to describe my ENT symptoms."
            )
           }
           className="mt-6 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500"
           >
           Start Symptom Assessment →
           </button>
           </div>

           <div className="hidden rounded-2xl border border-blue-400/20 bg-blue-500/10 p-4 sm:block">
           <Stethoscope className="h-10 w-10 text-blue-400" />
           </div>
            </div>
            </div>

           {/* Feature cards heading */}
           <div className="mb-4">
           <h3 className="text-lg font-semibold text-white">
            Explore your health tools
           </h3>

           <p className="mt-1 text-sm text-neutral-400">
           Choose a feature to get started.
           </p>
           </div>

           {/* Four feature cards */}
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">

    {/* Card 1 */}
    <button
      type="button"
      onClick={() =>
        setInputSymptom(
          "I would like to assess my ENT symptoms."
        )
      }
      className="group rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left transition duration-200 hover:-translate-y-1 hover:border-blue-400/40 hover:bg-blue-500/[0.07]"
    >
      <div className="mb-4 inline-flex rounded-xl bg-blue-500/10 p-3">
        <Stethoscope className="h-6 w-6 text-blue-400" />
      </div>

      <h4 className="font-semibold text-white">
        Check Symptoms
      </h4>

      <p className="mt-2 text-sm leading-6 text-neutral-400">
        Describe your symptoms and receive an AI-generated
        health-awareness assessment.
      </p>

      <span className="mt-4 block text-sm font-medium text-blue-400">
        Get started →
      </span>
    </button>

    {/* Card 2: Explore ENT Conditions */}
<button
  type="button"
  aria-expanded={conditionsOpen}
  onClick={() =>
    setConditionsOpen((previous) => !previous)
  }
  className="group rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left transition duration-200 hover:-translate-y-1 hover:border-teal-400/40 hover:bg-teal-500/[0.07]"
>
  <div className="mb-4 inline-flex rounded-xl bg-teal-500/10 p-3">
    <Activity className="h-6 w-6 text-teal-400" />
  </div>

  <h4 className="font-semibold text-white">
    Explore ENT Conditions
  </h4>

  <p className="mt-2 text-sm leading-6 text-neutral-400">
    Learn about the eight ENT conditions supported by your
    disease classifier and their common symptoms.
  </p>

  <span className="mt-4 block text-sm font-medium text-teal-400">
    {conditionsOpen
      ? "Close conditions ↑"
      : "Explore conditions →"}
  </span>
</button>
    {/* Card 3 */}
    <button
      type="button"
      onClick={() =>
        setInputSymptom(
          "I would like to assess my ENT symptoms and then explore how changing a symptom may affect the model prediction."
        )
      }
     className="group rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 text-left transition duration-200 hover:-translate-y-0.5 hover:border-teal-400/30 hover:bg-teal-500/[0.05]"
    >
      <div className="mb-4 inline-flex rounded-xl border border-teal-400/10 bg-teal-500/[0.08] p-3">
     <MessageSquare className="h-6 w-6 text-teal-400" />
     </div>

      <h4 className="font-semibold text-white">
        What-If Simulator
      </h4>

      <p className="mt-2 text-sm leading-6 text-neutral-400">
        Explore how adding or removing a symptom can change
        the model's predicted category.
      </p>

      <span className="mt-4 block text-sm font-medium text-teal-400">
  Explore simulation →
</span>
    </button>

    {/* Card 4 */}
    <button
      type="button"
      onClick={() =>
        setInputSymptom(
          "What ENT symptoms may require urgent medical attention, and when should a person seek professional medical care?"
        )
      }
      className="group rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left transition duration-200 hover:-translate-y-1 hover:border-amber-400/40 hover:bg-amber-500/[0.07]"
    >
      <div className="mb-4 inline-flex rounded-xl bg-amber-500/10 p-3">
        <ShieldAlert className="h-6 w-6 text-amber-400" />
      </div>

      <h4 className="font-semibold text-white">
        Health & Safety
      </h4>

      <p className="mt-2 text-sm leading-6 text-neutral-400">
        Learn about warning signs, appropriate medical care,
        and the chatbot's safety limitations.
      </p>

      <span className="mt-4 block text-sm font-medium text-amber-400">
        Learn more →
      </span>
    </button>

  </div>
{/* Safety note */}


{/* MEDICAL SAFETY BANNER */}
<div className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/[0.08] p-4 sm:p-5">
  <div className="flex items-start gap-3">
    <div className="shrink-0 rounded-xl border border-amber-400/20 bg-amber-500/10 p-2">
      <AlertTriangle className="h-6 w-6 text-amber-400" />
    </div>

    <div className="min-w-0">
      <h3 className="font-semibold text-amber-300">
        Medical Safety Alert
      </h3>

      <p className="mt-2 text-sm leading-6 text-neutral-200">
        If you have difficulty breathing, cannot swallow saliva,
        experience severe throat or neck swelling, or have rapidly
        worsening symptoms, seek emergency medical care immediately.
        Do not rely on this chatbot for urgent medical decisions.
      </p>

      <div className="mt-3 border-t border-amber-400/15 pt-3">
        <p className="text-xs leading-5 text-neutral-400">
          <strong className="text-neutral-200">Medical disclaimer:</strong>{" "}
          This chatbot provides general ENT health awareness and
          educational information only. It does not provide a medical
          diagnosis or replace a qualified healthcare professional.
          Consult a doctor for persistent, severe, or concerning symptoms.
        </p>
      </div>
    </div>
  </div>
</div>
{/* Expandable ENT Conditions Library */}
{conditionsOpen && (
  <div className="mt-6 rounded-2xl border border-teal-400/20 bg-white/[0.03] p-5">
    <div className="mb-5 flex items-center justify-between gap-3">
      <div>
        <h3 className="text-xl font-semibold text-white">
          Explore ENT Conditions
        </h3>

        <p className="mt-2 text-sm text-neutral-400">
          Eight conditions supported by your current classifier.
        </p>
      </div>

      <button
        type="button"
        onClick={() => setConditionsOpen(false)}
        className="rounded-lg border border-white/10 px-3 py-2 text-sm text-neutral-300 hover:bg-white/10"
      >
        Close
      </button>
    </div>

    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {[
        {
          name: "Acute sinusitis",
          description:
            "May cause nasal congestion, facial pressure, and nasal discharge.",
        },
        {
          name: "Chronic sinusitis",
          description:
            "May involve persistent congestion, facial pressure, and reduced sense of smell.",
        },
        {
          name: "Common cold",
          description:
            "May cause a runny nose, sneezing, congestion, and throat irritation.",
        },
        {
          name: "Laryngitis",
          description:
            "May cause hoarseness, voice changes, or temporary voice loss.",
        },
        {
          name: "Otitis externa (swimmer's ear)",
          description:
            "May cause outer-ear pain, itching, tenderness, or discharge.",
        },
        {
          name: "Pharyngitis",
          description:
            "May cause throat soreness, irritation, or painful swallowing.",
        },
        {
          name: "Seasonal allergies (hay fever)",
          description:
            "May cause sneezing, a runny or itchy nose, and itchy or watery eyes.",
        },
        {
          name: "Tonsillitis",
          description:
            "May cause a sore throat, swollen tonsils, fever, or discomfort when swallowing.",
        },
      ].map((condition) => (
        <div
          key={condition.name}
          className="rounded-xl border border-white/10 bg-neutral-900/60 p-4"
        >
          <h4 className="font-semibold text-teal-300">
            {condition.name}
          </h4>

          <p className="mt-2 text-sm leading-6 text-neutral-400">
            {condition.description}
          </p>
        </div>
      ))}
    </div>

    <p className="mt-4 text-xs leading-5 text-neutral-500">
      These descriptions are for general health awareness only.
      They do not confirm a diagnosis or replace professional medical advice.
    </p>
  </div>
)}
    <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-400/10 bg-amber-400/[0.04] p-4">
    <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />

    <p className="text-xs leading-5 text-neutral-400">
      This chatbot provides supportive health-awareness information
      and does not replace professional medical diagnosis or treatment.
      Seek urgent medical help for serious symptoms.
    </p>
  </div>
</motion.div>
          ) : (

            /* Messages */

            <div className="max-w-4xl mx-auto space-y-6">


              {messages.map(
                (msg, idx) => (

                  <motion.div

                    key={idx}

                    initial={{
                      opacity: 0,
                      y: 10,
                    }}

                    animate={{
                      opacity: 1,
                      y: 0,
                    }}

                    className={`flex flex-col ${
                      msg.role ===
                      "user"
                        ? "items-end"
                        : "items-start"
                    }`}
                  >

{/* Prediction */}

{msg.prediction && (

  <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold px-3 py-1 bg-blue-500/10 text-blue-300 rounded-full border border-blue-500/20 backdrop-blur-md ml-2">

    <span>
      Detected:{" "}
      {msg.prediction}
    </span>

    {msg.confidence && (
      <>
        <span className="w-1 h-1 bg-blue-400 rounded-full"></span>

        <span>
          {msg.confidence}
        </span>
      </>
    )}

  </div>

)}

                    {/* Explainability */}

                    {msg.explanation &&
                      msg.explanation.length >
                        0 && (

                        <div className="mb-2 ml-2 max-w-[85%] md:max-w-[80%] px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-sm">

                          <div className="font-semibold mb-2">

                            Key model-contributing symptoms

                          </div>


                          {msg.explanation.map(
                            (
                              item,
                              index
                            ) => (

                              <div
                                key={
                                  index
                                }

                                className="flex justify-between gap-4 py-1"
                              >

                                <span>

                                  {
                                    item.symptom
                                  }

                                </span>


                                <span>

                                  {item.contribution.toFixed(
                                    3
                                  )}

                                </span>

                              </div>

                            )
                          )}

                        </div>

                      )}


                    {/* Main assistant/user message */}

                    <div

                      className={`max-w-[85%] md:max-w-[80%] p-4 rounded-3xl text-sm md:text-base leading-relaxed shadow-lg backdrop-blur-md ${
                        msg.role ===
                        "user"

                          ? "bg-blue-600/90 text-white rounded-br-sm border border-blue-500/50"

                          : "bg-white/10 text-neutral-100 rounded-bl-sm border border-white/10"
                      }`}
                    >

                      {msg.content}

                    </div>


                    {/* Follow-up question */}

                    {msg.role ===
                      "assistant" &&
                      msg.followup_question && (

                        <div className="mt-3 ml-2 max-w-[85%] md:max-w-[80%] px-4 py-3 bg-blue-500/10 border border-blue-500/20 rounded-2xl text-sm text-blue-200">

                          <span className="font-semibold">

                            Follow-up question:{" "}

                          </span>

                          {
                            msg.followup_question
                          }

                        </div>

                      )}


                    {/* Personalized Guidance */}

                    {msg.role ===
                      "assistant" &&
                      msg.guidance && (

                        <div className="mt-3 ml-2 max-w-[85%] md:max-w-[80%] px-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-sm">


                          <div className="font-semibold mb-4">

                            Personalized Guidance

                          </div>


                          {/* DO */}

                          {msg.guidance.do &&
                            msg.guidance.do.length >
                              0 && (

                              <div className="mb-4">

                                <div className="font-semibold mb-2">

                                  DO

                                </div>


                                <ul className="list-disc ml-5 space-y-1">

                                  {msg.guidance.do.map(
                                    (
                                      item,
                                      index
                                    ) => (

                                      <li
                                        key={
                                          index
                                        }
                                      >

                                        {item}

                                      </li>

                                    )
                                  )}

                                </ul>

                              </div>

                            )}


                          {/* DON'T */}

                          {msg.guidance.dont &&
                            msg.guidance.dont.length >
                              0 && (

                              <div className="mb-4">

                                <div className="font-semibold mb-2">

                                  DON'T

                                </div>


                                <ul className="list-disc ml-5 space-y-1">

                                  {msg.guidance.dont.map(
                                    (
                                      item,
                                      index
                                    ) => (

                                      <li
                                        key={
                                          index
                                        }
                                      >

                                        {item}

                                      </li>

                                    )
                                  )}

                                </ul>

                              </div>

                            )}


                          {/* MONITOR */}

                          {msg.guidance.monitor &&
                            msg.guidance.monitor.length >
                              0 && (

                              <div>

                                <div className="font-semibold mb-2">

                                  MONITOR

                                </div>


                                <ul className="list-disc ml-5 space-y-1">

                                  {msg.guidance.monitor.map(
                                    (
                                      item,
                                      index
                                    ) => (

                                      <li
                                        key={
                                          index
                                        }
                                      >

                                        {item}

                                      </li>

                                    )
                                  )}

                                </ul>

                              </div>

                            )}

                        </div>

                      )}

                  </motion.div>

                )
              )}

            </div>

          )}


          {/* Loading animation */}

          {loading && (

            <div className="max-w-4xl mx-auto">

              <motion.div

                initial={{
                  opacity: 0,
                }}

                animate={{
                  opacity: 1,
                }}

                className="flex items-start mt-6"
              >

                <div className="bg-white/10 border border-white/10 p-4 rounded-3xl rounded-bl-sm flex gap-2 backdrop-blur-md shadow-lg">

                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></span>

                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100"></span>

                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200"></span>

                </div>

              </motion.div>

            </div>

          )}


          <div
            ref={messagesEndRef}
            className="h-4"
          />

        </div>


        {/* ====================================================
            PHASE 8 - WHAT-IF
        ==================================================== */}

        {messages.some(

          (msg) =>
            msg.role ===
              "assistant" &&
            msg.symptoms &&
            msg.symptoms.length >
              0

        ) && (

          <div className="px-4 md:px-6 pb-2 z-10">

            <div className="max-w-4xl mx-auto">

              <div className="bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-md">


                <div className="flex items-center justify-between mb-3">

                  <div>

                    <h3 className="text-sm font-semibold text-neutral-200">

                      What-If Symptom Simulation

                    </h3>


                    <p className="text-xs text-neutral-500 mt-1">

                      Explore how adding or removing a symptom changes the model prediction.

                    </p>

                  </div>


                  <button

                    onClick={() =>
                      setWhatIfOpen(
                        !whatIfOpen
                      )
                    }

                    className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"
                  >

                    {whatIfOpen
                      ? "Close"
                      : "Open"}

                  </button>

                </div>


                {whatIfOpen && (

                  <div className="space-y-3">


                    <div className="flex gap-2">

                      <button

                        onClick={() =>
                          setWhatIfMode(
                            "add"
                          )
                        }

                        className={`px-3 py-1.5 rounded-lg text-xs ${
                          whatIfMode ===
                          "add"

                            ? "bg-blue-600 text-white"

                            : "bg-white/5 text-neutral-400"
                        }`}
                      >

                        Add Symptom

                      </button>


                      <button

                        onClick={() =>
                          setWhatIfMode(
                            "remove"
                          )
                        }

                        className={`px-3 py-1.5 rounded-lg text-xs ${
                          whatIfMode ===
                          "remove"

                            ? "bg-blue-600 text-white"

                            : "bg-white/5 text-neutral-400"
                        }`}
                      >

                        Remove Symptom

                      </button>

                    </div>


                    <div className="flex gap-2">

                      <input

                        type="text"

                        value={
                          whatIfSymptom
                        }

                        onChange={(e) =>
                          setWhatIfSymptom(
                            e.target.value
                          )
                        }

                        placeholder={
                          whatIfMode ===
                          "add"

                            ? "Enter symptom to add..."

                            : "Enter symptom to remove..."
                        }

                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      />


                      <button

                        onClick={
                          handleWhatIf
                        }

                        disabled={
                          whatIfLoading ||
                          !whatIfSymptom.trim()
                        }

                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white rounded-lg text-sm"
                      >

                        {whatIfLoading
                          ? "Simulating..."
                          : "Simulate"}

                      </button>

                    </div>


                    {whatIfResult && (

                      <div className="mt-4 bg-black/20 border border-white/10 rounded-xl p-4">


                        <div className="text-xs text-neutral-500 mb-2">

                          What-If Result

                        </div>


                        <div className="text-sm text-neutral-200">

                          <span className="font-semibold">

                            Prediction:

                          </span>{" "}

                          {
                            whatIfResult.prediction
                          }

                        </div>


                        <div className="text-sm text-neutral-200 mt-1">

                          <span className="font-semibold">

                            Confidence:

                          </span>{" "}

                          {
                            whatIfResult.confidence
                          }%

                        </div>


                        <div className="text-xs text-neutral-500 mt-3">

                          Modified symptoms:

                        </div>


                        <div className="flex flex-wrap gap-2 mt-2">

                          {whatIfResult.symptoms.map(
                            (
                              symptom
                            ) => (

                              <span

                                key={
                                  symptom
                                }

                                className="px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-xs text-blue-300"
                              >

                                {
                                  symptom
                                }

                              </span>

                            )
                          )}

                        </div>

                      </div>

                    )}

                  </div>

                )}

              </div>

            </div>

          </div>

        )}


        {/* ====================================================
            INPUT AREA
        ==================================================== */}

        <div className="p-4 md:p-6 bg-gradient-to-t from-neutral-950 via-neutral-950/80 to-transparent z-10">


          {/* Voice language selector */}

          <div className="max-w-4xl mx-auto mb-2 flex justify-end">

            <select

              value={
                speechLanguage
              }

              onChange={(e) =>
                setSpeechLanguage(
                  e.target.value
                )
              }

              disabled={
                loading ||
                isListening
              }

              className="bg-white/5 border border-white/10 text-neutral-400 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >

              <option value="en-IN">
                English
              </option>

              <option value="te-IN">
                తెలుగు
              </option>

              <option value="ta-IN">
                தமிழ்
              </option>

              <option value="hi-IN">
                हिन्दी
              </option>

            </select>

          </div>


          {/* Input */}

          <div className="relative flex items-center max-w-4xl mx-auto group">


            <input

              type="text"

              disabled={
                !isSignedIn ||
                loading
              }

              className="w-full bg-white/5 border border-white/10 text-neutral-100 placeholder-neutral-500 rounded-full pl-6 pr-28 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all shadow-[0_4px_30px_rgba(0,0,0,0.5)] backdrop-blur-xl disabled:opacity-50"

              placeholder={
                isSignedIn
                  ? "Tell me how you're feeling..."
                  : "Sign in to send a message"
              }

              value={
                inputSymptom
              }

              onChange={(e) =>
                setInputSymptom(
                  e.target.value
                )
              }

              onKeyDown={(e) => {

                if (
                  e.key ===
                  "Enter"
                ) {

                  handleSend();

                }

              }}

            />


            {/* =================================================
                VOICE BUTTON
            ================================================= */}

            <button

              type="button"

              onClick={
                handleVoiceInput
              }

              disabled={
                !isSignedIn ||
                loading
              }

              title={
                isListening
                  ? "Stop voice input"
                  : "Start voice input"
              }

              className={`absolute right-14 p-3 rounded-full transition-colors flex items-center justify-center ${
                isListening

                  ? "bg-red-600 hover:bg-red-500 text-white shadow-[0_0_15px_rgba(220,38,38,0.4)]"

                  : "bg-white/10 hover:bg-white/20 text-neutral-300"
              } disabled:bg-neutral-800 disabled:text-neutral-600`}
            >

              {isListening ? (

                <MicOff className="w-5 h-5" />

              ) : (

                <Mic className="w-5 h-5" />

              )}

            </button>


            {/* =================================================
                SEND BUTTON
            ================================================= */}

            <button

              type="button"

              onClick={
                handleSend
              }

              disabled={

                !isSignedIn ||

                loading ||

                !inputSymptom.trim()

              }

              title="Send message"

              className="absolute right-2 p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white rounded-full transition-colors flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.4)] disabled:shadow-none"
            >

              <Send className="w-5 h-5 ml-0.5" />

            </button>

          </div>     
          <p className="px-3 py-2 text-center text-xs leading-5 text-neutral-400">
         For health awareness only — not a diagnosis or a substitute for
         professional medical advice. Consult a healthcare professional for
         persistent, severe, or concerning symptoms.
         </p>

        </div>

      </div>

    </div>

  );

}