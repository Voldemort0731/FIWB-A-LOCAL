"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_URL, standardize_email } from '@/utils/config';

interface AcademicContextType {
    courses: any[];
    gmailMaterials: any[];
    loading: boolean;
    syncing: boolean;
    error: string | null;
    refreshData: () => Promise<void>;
    startSync: () => Promise<void>;
}

const AcademicContext = createContext<AcademicContextType | undefined>(undefined);

export function AcademicProvider({ children }: { children: React.ReactNode }) {
    const [courses, setCourses] = useState<any[]>([]);
    const [gmailMaterials, setGmailMaterials] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refreshData = useCallback(async () => {
        const rawEmail = typeof window !== 'undefined' ? localStorage.getItem("user_email") : null;
        if (!rawEmail) {
            setLoading(false);
            return;
        }

        const email = standardize_email(rawEmail);

        // 1. Course Fetch (Global Critical Path)
        const fetchCourses = async () => {
            try {
                const res = await fetch(`${API_URL}/api/courses/?user_email=${email}`);
                if (res.ok) {
                    const data = await res.json();
                    setCourses(data);
                    setError(null);
                }
            } catch (err) {
                console.error("Failed to fetch courses", err);
                if (courses.length === 0) setError("Academic engine offline.");
            } finally {
                // Important: Unblock UI as soon as courses are back
                setLoading(false);
            }
        };

        // 2. Gmail Fetch (Secondary Path)
        const fetchGmail = async () => {
            try {
                const res = await fetch(`${API_URL}/api/courses/GMAIL_INBOX/materials?user_email=${email}`);
                if (res.ok) {
                    const data = await res.json();
                    if (Array.isArray(data)) {
                        setGmailMaterials(data);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch gmail materials", err);
            }
        };

        // Fire and forget or parallelize without blocking initialization
        await Promise.allSettled([fetchCourses(), fetchGmail()]);
    }, [courses.length]);

    const startSync = useCallback(async () => {
        const rawEmail = localStorage.getItem("user_email");
        if (!rawEmail) return;

        const email = standardize_email(rawEmail);

        setSyncing(true);
        try {
            await fetch(`${API_URL}/api/admin/sync/${email}`, { method: "POST" });
            // The sync runs in background, but we refresh after a bit to show progress
            setTimeout(refreshData, 3000);
            setTimeout(refreshData, 8000);

            // Keep syncing state active for at least 5s for better UX feel
            setTimeout(() => setSyncing(false), 5000);
        } catch (e) {
            console.error("Sync trigger failed", e);
            setSyncing(false);
        }
    }, [refreshData]);

    useEffect(() => {
        refreshData();

        // Auto-refresh every 5 minutes while active
        const interval = setInterval(refreshData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [refreshData]);

    return (
        <AcademicContext.Provider value={{
            courses,
            gmailMaterials,
            loading,
            syncing,
            error,
            refreshData,
            startSync
        }}>
            {children}
        </AcademicContext.Provider>
    );
}

export function useAcademic() {
    const context = useContext(AcademicContext);
    if (context === undefined) {
        throw new Error('useAcademic must be used within an AcademicProvider');
    }
    return context;
}
