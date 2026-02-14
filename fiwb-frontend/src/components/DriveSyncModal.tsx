"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Folder, X, Check, Loader2, Cloud, Search, ChevronRight } from "lucide-react";
import { API_URL } from "@/utils/config";
import clsx from "clsx";

interface DriveSyncModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function DriveSyncModal({ isOpen, onClose }: DriveSyncModalProps) {
    const [folders, setFolders] = useState<any[]>([]);
    const [selectedFolders, setSelectedFolders] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        if (isOpen) {
            fetchFolders();
        }
    }, [isOpen]);

    const fetchFolders = async () => {
        const email = localStorage.getItem("user_email");
        if (!email) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/drive/folders?user_email=${email}`);
            const data = await res.json();
            if (res.ok && Array.isArray(data)) {
                setFolders(data);
            } else {
                console.error("Failed to fetch folders:", data);
                setFolders([]);
            }
        } catch (e) {
            console.error("Failed to fetch folders", e);
        } finally {
            setLoading(false);
        }
    };

    const toggleFolder = (id: string) => {
        setSelectedFolders(prev =>
            prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]
        );
    };

    const handleSync = async () => {
        const email = localStorage.getItem("user_email");
        if (!email || selectedFolders.length === 0) return;

        setSyncing(true);
        try {
            await fetch(`${API_URL}/api/drive/sync`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_email: email,
                    folder_ids: selectedFolders
                })
            });
            onClose();
            alert(`Sync started for ${selectedFolders.length} folders. Check back in a few minutes!`);
        } catch (e) {
            console.error("Sync failed", e);
        } finally {
            setSyncing(false);
        }
    };

    const filteredFolders = Array.isArray(folders) ? folders.filter(f =>
        f.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) : [];

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
                        className="relative w-full max-w-2xl bg-white dark:bg-[#0a0a0a] border border-gray-100 dark:border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col max-h-[80vh] transition-colors duration-500"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="p-8 border-b border-gray-100 dark:border-white/5 flex justify-between items-center bg-gradient-to-r from-blue-600/5 to-transparent transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-gray-50 dark:bg-black/40 rounded-2xl flex items-center justify-center border border-gray-200 dark:border-white/10 shadow-xl">
                                    <Cloud className="text-blue-600 dark:text-blue-400" size={24} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">Sync Academic Drive</h3>
                                    <p className="text-xs text-gray-600 dark:text-gray-500 font-bold uppercase tracking-widest leading-relaxed">
                                        Select folders to feed your Digital Twin • <span className="text-amber-600 dark:text-amber-500/80 italic">Tip: Re-login if folders don't appear</span>
                                    </p>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-white/5 rounded-full transition-colors text-gray-500 dark:text-gray-400">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Search */}
                        <div className="px-8 py-4 border-b border-gray-100 dark:border-white/5 bg-gray-50/50 dark:bg-white/2 transition-colors">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-600 group-focus-within:text-blue-600 dark:group-focus-within:text-blue-500 transition-colors" size={16} />
                                <input
                                    type="text"
                                    placeholder="Search folders..."
                                    className="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/5 rounded-xl py-3 pl-12 pr-4 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-blue-600/50 dark:focus:border-blue-500/50 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-600"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* List */}
                        <div className="flex-1 overflow-y-auto p-4 scrollbar-premium">
                            {loading ? (
                                <div className="h-64 flex flex-col items-center justify-center gap-4 text-gray-500">
                                    <Loader2 className="animate-spin text-blue-500" size={32} />
                                    <span className="text-sm font-black uppercase tracking-[0.2em]">Listing Vaults...</span>
                                </div>
                            ) : filteredFolders.length === 0 ? (
                                <div className="h-64 flex flex-col items-center justify-center text-center p-8">
                                    <Folder className="text-gray-800 mb-4" size={48} />
                                    <p className="text-gray-500 font-medium">No folders found in your root Drive.</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-2">
                                    {filteredFolders.map(folder => (
                                        <div
                                            key={folder.id}
                                            onClick={() => toggleFolder(folder.id)}
                                            className={clsx(
                                                "group flex items-center justify-between p-4 rounded-2xl transition-all cursor-pointer border transition-colors",
                                                selectedFolders.includes(folder.id)
                                                    ? "bg-blue-600 text-white border-blue-400 shadow-xl shadow-blue-500/20"
                                                    : "hover:bg-gray-50 dark:hover:bg-white/5 border-gray-100 dark:border-transparent text-gray-600 dark:text-gray-400"
                                            )}
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className={clsx(
                                                    "w-10 h-10 rounded-xl flex items-center justify-center transition-colors",
                                                    selectedFolders.includes(folder.id) ? "bg-white/20" : "bg-gray-100 dark:bg-white/5"
                                                )}>
                                                    <Folder size={20} className={selectedFolders.includes(folder.id) ? "text-white" : "text-gray-400 dark:text-gray-600"} />
                                                </div>
                                                <span className="font-black text-sm tracking-tight">{folder.name}</span>
                                            </div>
                                            <div className={clsx(
                                                "w-6 h-6 rounded-lg border flex items-center justify-center transition-all",
                                                selectedFolders.includes(folder.id)
                                                    ? "bg-blue-600 border-blue-400 text-white"
                                                    : "border-white/10 group-hover:border-white/20 text-transparent"
                                            )}>
                                                <Check size={14} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
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
                                    disabled={syncing || selectedFolders.length === 0}
                                    className="flex-[2] py-4 bg-blue-600 dark:bg-white text-white dark:text-black hover:bg-blue-500 dark:hover:bg-white/90 disabled:opacity-30 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2 uppercase tracking-widest shadow-2xl shadow-blue-500/10"
                                >
                                    {syncing ? (
                                        <Loader2 className="animate-spin" size={18} />
                                    ) : (
                                        <>
                                            Inject Selected ({selectedFolders.length})
                                            <ChevronRight size={18} />
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
