"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, ExternalLink, Calendar, User } from "lucide-react";

interface GmailPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    email: any;
}

export default function GmailPreviewModal({ isOpen, onClose, email }: GmailPreviewModalProps) {
    if (!email) return null;

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={onClose}
                    />

                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="relative w-full max-w-2xl bg-white dark:bg-[#0a0a0a] border border-gray-100 dark:border-white/10 rounded-[2rem] shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="p-6 border-b border-gray-100 dark:border-white/5 flex justify-between items-start bg-gray-50/50 dark:bg-white/5">
                            <div className="flex gap-4 pr-8">
                                <div className="p-3 bg-white dark:bg-white/10 rounded-xl shadow-sm border border-gray-100 dark:border-white/5 h-fit">
                                    <Mail className="text-red-500" size={24} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-gray-900 dark:text-white leading-tight mb-2">
                                        {email.title}
                                    </h3>
                                    <div className="flex flex-wrap gap-3 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        <div className="flex items-center gap-1.5">
                                            <Calendar size={12} />
                                            {(email.date === "Recent" || (!email.date && !email.created_at))
                                                ? "Recent"
                                                : new Date(email.created_at || email.date).toLocaleDateString(undefined, {
                                                    weekday: 'long',
                                                    year: 'numeric',
                                                    month: 'long',
                                                    day: 'numeric'
                                                })}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-gray-200 dark:hover:bg-white/10 rounded-full transition-colors text-gray-500"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="p-8 overflow-y-auto scrollbar-premium flex-1">
                            <div className="prose dark:prose-invert prose-sm max-w-none">
                                <p className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 leading-relaxed text-sm">
                                    {(email.content || email.description || "")
                                        .split('\n\nCONTENT:')[0]
                                        .replace('SUMMARY: ', '')
                                        .trim() || "No content available."}
                                </p>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="p-6 border-t border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-black flex justify-end gap-3">
                            <button
                                onClick={onClose}
                                className="px-6 py-3 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-gray-300 rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-gray-50 dark:hover:bg-white/10 transition-all"
                            >
                                Close
                            </button>
                            <button
                                onClick={() => {
                                    const userEmail = localStorage.getItem("user_email");
                                    if (email.id && userEmail) {
                                        // "search isnt working" implies #search/ID returned no results.
                                        // Switch to #all/ID which opens the thread directly by ID
                                        // Keep /mail/u/?authuser= to handle account switching
                                        const cleanId = email.id.trim();
                                        window.open(`https://mail.google.com/mail/u/?authuser=${encodeURIComponent(userEmail)}#all/${cleanId}`, '_blank');
                                    } else {
                                        window.open(email.source_link || "https://mail.google.com", '_blank');
                                    }
                                }}
                                className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-blue-500 shadow-lg shadow-blue-500/20 active:scale-95 transition-all flex items-center gap-2"
                            >
                                Open in Gmail
                                <ExternalLink size={14} />
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
