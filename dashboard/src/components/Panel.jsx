export default function Panel({ title, right, children, className = "" }) {
  return (
    <section
      className={`rounded-xl border border-slate-800 bg-[#0d1526]/80 ${className}`}
    >
      <header className="flex items-center justify-between border-b border-slate-800/70 px-4 py-2.5">
        <h2 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
          <span className="inline-block h-3 w-1 rounded-sm bg-cyan-400" />
          {title}
        </h2>
        {right}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}
