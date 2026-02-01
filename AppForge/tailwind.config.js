/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: '#e0f2fe',
                    100: '#bae6fd',
                    200: '#7dd3fc',
                    300: '#38bdf8',
                    400: '#0ea5e9',
                    500: '#0284c7',
                    600: '#0369a1',
                    700: '#075985',
                },
                accent: {
                    400: '#c084fc',
                    500: '#a855f7',
                    600: '#9333ea',
                },
            },
            fontFamily: {
                display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
            },
            boxShadow: {
                inner: 'inset 0 1px 2px rgba(15,23,42,0.6)',
            },
        },
    },
    plugins: [],
}
