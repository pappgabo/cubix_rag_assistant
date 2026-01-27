"use client";

import { useState } from "react";

export default function HomePage() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleAsk = async () => {
        setError(null);
        setAnswer(null);

        if (!question.trim()) {
            setError("Írj be egy kérdést!");
            return;
        }

        setLoading(true);
        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ question }),
            });

            const data = await res.json();

            if (!res.ok) {
                setError(data.error || "Ismeretlen hiba.");
            } else {
                setAnswer(data.answer ?? "Nincs answer mező a válaszban.");
            }
        } catch (e) {
            setError("Nem sikerült elérni a szervert.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "sans-serif" }}>
            <h1>Receptes AI asszisztens</h1>

            <label style={{ display: "block", marginBottom: "0.5rem" }}>
                Kérdés:
            </label>
            <textarea
                rows={4}
                style={{ width: "100%", marginBottom: "0.5rem" }}
                placeholder="Írd ide a kérdésed..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
            />

            <button onClick={handleAsk} disabled={loading}>
                {loading ? "Gondolkodom..." : "Küldés"}
            </button>

            {error && (
                <p style={{ color: "red", marginTop: "1rem" }}>
                    {error}
                </p>
            )}

            {answer && (
                <div style={{ marginTop: "1.5rem", padding: "1rem", border: "1px solid #ddd" }}>
                    <h2>Válasz</h2>
                    <p>{answer}</p>
                </div>
            )}
        </main>
    );
}