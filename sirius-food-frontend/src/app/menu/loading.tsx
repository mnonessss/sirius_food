export default function MenuLoading() {
    return (
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="h-9 w-40 animate-pulse rounded-lg bg-neutral-200" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-32 animate-pulse rounded-2xl bg-white" />
          ))}
        </div>
      </main>
    );
  }