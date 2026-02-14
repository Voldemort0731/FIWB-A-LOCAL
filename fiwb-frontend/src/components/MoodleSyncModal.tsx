"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Check, Loader2, Globe, Key, ChevronRight, GraduationCap } from "lucide-react";
import { API_URL } from "@/utils/config";
import clsx from "clsx";

interface MoodleSyncModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function MoodleSyncModal({ isOpen, onClose }: MoodleSyncModalProps) {
    const [url, setUrl] = useState("");
    const [token, setToken] = useState("");
    const [syncing, setSyncing] = useState(false);
    const [message, setMessage] = useState("");

    const handleConnect = async () => {
        const email = localStorage.getItem("user_email");
        if (!email || !url || !token) return;

        setSyncing(true);
        setMessage("");
        try {
            const res = await fetch(`${API_URL}/api/moodle/connect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_email: email,
                    moodle_url: url,
                    moodle_token: token
                })
            });
            const data = await res.json();
            if (res.ok) {
                setMessage("Successfully connected! Syncing started in background.");
                setTimeout(() => {
                    onClose();
                }, 2000);
            } else {
                setMessage(data.detail || "Connection failed.");
            }
        } catch (e) {
            console.error("Moodle connection failed", e);
            setMessage("Network error. Is the backend running?");
        } finally {
            setSyncing(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 bg-black/80 backdrop-blur-xl"
                        onClick={onClose}
                    />

                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="relative w-full max-w-lg bg-[#0a0a0a] border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="p-8 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-orange-600/5 to-transparent">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 glass-card rounded-2xl flex items-center justify-center border border-white/10">
                                    <GraduationCap className="text-orange-400" size={24} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-white tracking-tight">Connect Moodle LMS</h3>
                                    <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">Bridge your institutional intelligence</p>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-gray-400">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Form */}
                        <div className="p-8 space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Moodle Site URL</label>
                                <div className="relative group">
                                    <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-orange-500 transition-colors" size={16} />
                                    <input
                                        type="text"
                                        placeholder="https://moodle.youruniversity.edu"
                                        className="w-full bg-white/5 border border-white/5 rounded-xl py-3.5 pl-12 pr-4 text-sm focus:outline-none focus:border-orange-500/50 transition-all text-white font-medium"
                                        value={url}
                                        onChange={(e) => setUrl(e.target.value)}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Web Service Token</label>
                                <div className="relative group">
                                    <Key className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-orange-500 transition-colors" size={16} />
                                    <input
                                        type="password"
                                        placeholder="Your Moodle API Token"
                                        className="w-full bg-white/5 border border-white/5 rounded-xl py-3.5 pl-12 pr-4 text-sm focus:outline-none focus:border-orange-500/50 transition-all text-white font-medium"
                                        value={token}
                                        onChange={(e) => setToken(e.target.value)}
                                    />
                                </div>
                                <p className="text-[10px] text-gray-600 font-medium leading-relaxed mt-2 px-1">
                                    Enable Web Services in Moodle settings and generate a token for the "FIWB AI" service to allow synchronization.
                                </p>
                            </div>

                            {message && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={clsx(
                                        "p-4 rounded-xl text-xs font-bold border",
                                        message.includes("success") ? "bg-green-500/10 border-green-500/20 text-green-400" : "bg-red-500/10 border-red-500/20 text-red-400"
                                    )}
                                >
                                    {message}
                                </motion.div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="p-8 border-t border-white/5 bg-black/40">
                            <button
                                onClick={handleConnect}
                                disabled={syncing || !url || !token}
                                className="w-full py-4 bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-30 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2 uppercase tracking-widest shadow-2xl shadow-orange-500/20"
                            >
                                {syncing ? (
                                    <Loader2 className="animate-spin" size={18} />
                                ) : (
                                    <>
                                        Establish Connection
                                        <ChevronRight size={18} />
                                    </>
                                )}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
