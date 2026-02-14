"use client";
import React from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
    // User should replace this.
    const clientId = "46647341779-d5dtuag91cnfdnj44q6p8qq62toi8sod.apps.googleusercontent.com";

    return (
        <GoogleOAuthProvider clientId={clientId}>
            {children}
        </GoogleOAuthProvider>
    );
}
