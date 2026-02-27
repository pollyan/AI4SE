/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./*.{js,ts,jsx,tsx}",
        "./src/**/*.{js,ts,jsx,tsx}",
        "./components/**/*.{js,ts,jsx,tsx}",
        "./hooks/**/*.{js,ts,jsx,tsx}",
        "./services/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#6366f1", // Indigo 500
                secondary: "#8b5cf6", // Violet 500
                "background-light": "#f3f4f6", // Gray 100
                "background-dark": "#111827", // Gray 900
                "surface-light": "#ffffff",
                "surface-dark": "#1f2937", // Gray 800
                "border-light": "#e5e7eb", // Gray 200
                "border-dark": "#374151", // Gray 700
            },
            fontFamily: {
                sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', '"Noto Sans"', 'sans-serif', '"Apple Color Emoji"', '"Segoe UI Emoji"', '"Segoe UI Symbol"', '"Noto Color Emoji"'],
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
        // require('@tailwindcss/forms'), // Optional, add if needed
    ],
    darkMode: 'class',
}
