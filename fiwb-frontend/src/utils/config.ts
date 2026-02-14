export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

export const standardize_email = (email: string | null): string => {
    if (!email) return "";
    const lowerEmail = email.toLowerCase().trim();
    if (lowerEmail === "sidwagh724@gmail.com") return "siddhantwagh724@gmail.com";
    return lowerEmail;
};
