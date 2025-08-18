export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background:
          "linear-gradient(135deg, var(--kb-bg-canvas) 0%, var(--kb-bg-surface) 100%)",
        color: "var(--kb-text)",
      }}
    >
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
