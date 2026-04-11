import { Toaster } from "@/components/ui/sonner"

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="container mx-auto p-4">
        <h1 className="text-2xl font-semibold">Lisa</h1>
        <p className="text-sm text-muted-foreground">Dashboard loading...</p>
      </main>
      <Toaster />
    </div>
  )
}

export default App
