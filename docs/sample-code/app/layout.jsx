import './globals.css';
import Navbar from "../components/navbar";

export const metadata = {
  title: 'Kaboom.ai Sample',
  description: 'Sample UI migrated to Next.js with Tailwind',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-canvas text-text">
        <Navbar />
        {children}
        <footer className="kb-container mt-10 pb-8 text-sm text-muted">
          © 2025 Kaboom.ai — Sample UI built from the design system
        </footer>
      </body>
    </html>
  );
}
