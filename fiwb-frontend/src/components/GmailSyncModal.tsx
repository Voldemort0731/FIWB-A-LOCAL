"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, X, Check, Loader2, RefreshCw } from "lucide-react";
import { API_URL } from "@/utils/config";

interface GmailSyncModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSyncSuccess?: () => void;
}

export default function GmailSyncModal({ isOpen, onClose, onSyncSuccess }: GmailSyncModalProps) {
    const [syncing, setSyncing] = useState(false);
    const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
    const [message, setMessage] = useState("");

    const handleSync = async () => {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            setMessage("User ID not found. Please re-login.");
            setStatus("error");
            return;
        }

        setSyncing(true);
        setStatus("idle");
        setMessage("");

        try {
            const res = await fetch(`${API_URL}/api/gmail/trigger/${userId}`, {
                method: "POST",
            });

            if (res.ok) {
                setStatus("success");
                setMessage("Sync started in background! Refreshing your inbox...");
                if (onSyncSuccess) onSyncSuccess();
                setTimeout(onClose, 2000);
            } else {
                const data = await res.json();
                setStatus("error");
                setMessage(data.detail || "Failed to start sync.");
            }
        } catch (e) {
            console.error("Sync failed", e);
            setStatus("error");
            setMessage("Network error. Please try again.");
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
                        className="relative w-full max-w-md bg-white dark:bg-[#0a0a0a] border border-gray-100 dark:border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col transition-colors duration-500"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="p-8 border-b border-gray-100 dark:border-white/5 flex justify-between items-center bg-gradient-to-r from-red-600/5 to-transparent transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-gray-50 dark:bg-black/40 rounded-2xl flex items-center justify-center border border-gray-200 dark:border-white/10 shadow-xl">
                                    <Mail className="text-red-600 dark:text-red-400" size={24} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">Sync Gmail</h3>
                                    <p className="text-xs text-gray-600 dark:text-gray-500 font-bold uppercase tracking-widest leading-relaxed">
                                        Scan for Tests & Announcements
                                    </p>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-white/5 rounded-full transition-colors text-gray-500 dark:text-gray-400">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-8 space-y-6">
                            <p className="text-gray-700 dark:text-gray-400 font-medium text-sm leading-relaxed">
                                This will scan your entire academic repository for:
                            </p>
                            <ul className="space-y-3">
                                {[
                                    "Upcoming tests, exams, and quizzes",
                                    "Class cancellations or room changes",
                                    "Important assignment updates"
                                ].map((item, i) => (
                                    <li key={i} className="flex items-center gap-3 text-sm font-semibold text-gray-800 dark:text-gray-300">
                                        <div className="w-6 h-6 rounded-full bg-green-500/10 flex items-center justify-center text-green-600 dark:text-green-400">
                                            <Check size={12} strokeWidth={3} />
                                        </div>
                                        {item}
                                    </li>
                                ))}
                            </ul>

                            {message && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`p-4 rounded-xl text-xs font-bold border ${stateStyles[status]}`}
                                >
                                    {message}
                                </motion.div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="p-8 border-t border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-black transition-colors">
                            <div className="flex gap-4">
                                <button
                                    onClick={onClose}
                                    className="flex-1 py-4 bg-white dark:bg-transparent border border-gray-200 dark:border-white/5 rounded-2xl font-black text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-all transition-colors uppercase tracking-widest"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSync}
                                    disabled={syncing}
                                    className="flex-[2] py-4 bg-blue-600 dark:bg-white text-white dark:text-black hover:bg-blue-500 dark:hover:bg-white/90 disabled:opacity-30 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2 uppercase tracking-widest shadow-2xl shadow-blue-500/10"
                                >
                                    {syncing ? (
                                        <>
                                            <Loader2 className="animate-spin" size={18} />
                                            Scanning...
                                        </>
                                    ) : (
                                        <>
                                            <RefreshCw size={18} />
                                            Start Scan
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

const stateStyles = {
    idle: "bg-gray-500/10 border-gray-500/20 text-gray-400",
    success: "bg-green-500/10 border-green-500/20 text-green-400",
    error: "bg-red-500/10 border-red-500/20 text-red-400"
};
