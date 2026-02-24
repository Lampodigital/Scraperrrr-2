import NeuralBackground from "@/components/ui/flow-field-background";

export default function NeuralHeroDemo() {
    return (
        // Container must have a defined height, or use h-screen
        <div className="relative w-full h-[300px] mb-8 rounded-3xl overflow-hidden border border-white/10">
            <NeuralBackground
                color="#BFF549" // Using the primary color from Glaido
                trailOpacity={0.1} // Lower = longer trails
                speed={0.8}
                particleCount={400}
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
                <h2 className="text-white text-3xl font-black mb-2 font-outfit uppercase tracking-tighter">
                    Premium AI Feed
                </h2>
                <p className="text-white/60 text-sm max-w-md">
                    Experience the latest in artificial intelligence with our high-fidelity, curated newsletter and community feed.
                </p>
            </div>
        </div>
    );
}
