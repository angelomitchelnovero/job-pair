import Link from "next/link";
import { ArrowRight, Sparkles, GitBranch, BarChart3, Shield, FileText } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="grid lg:grid-cols-2 gap-10 items-center pt-6">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs text-brand-700">
            <Sparkles className="w-3 h-3" /> Explainable AI matching
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-gray-900">
            See exactly how well your resume fits the role.
          </h1>
          <p className="text-lg text-gray-600">
            JobPair.aloe scores resume → job description pairs using a
            scikit-learn TF-IDF/cosine baseline and a PyTorch neural matcher.
            No black-box scores — every percentage has a reason.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/analyze" className="btn-primary">
              Analyze a match <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
            <Link href="/dashboard" className="btn-secondary">
              Open dashboard
            </Link>
          </div>
          <div className="flex gap-6 pt-4 text-sm text-gray-500">
            <span>• Scikit-learn + PyTorch</span>
            <span>• FastAPI + Next.js</span>
            <span>• PostgreSQL</span>
          </div>
        </div>
        <div className="card p-6 space-y-4">
          <ScoreDemoCard />
        </div>
      </section>

      <section className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <Feature
          icon={<FileText className="w-5 h-5 text-brand-600" />}
          title="Parse resumes & JDs"
          text="Extract skills, experience, education, certifications, and projects from PDF + free-form text."
        />
        <Feature
          icon={<GitBranch className="w-5 h-5 text-brand-600" />}
          title="Two real models"
          text="A linear/ridge + classifier scikit-learn baseline, and a small PyTorch MLP trained on engineered features."
        />
        <Feature
          icon={<BarChart3 className="w-5 h-5 text-brand-600" />}
          title="Explainable scores"
          text="See matching skills, gaps, experience alignment, and the feature weights behind each prediction."
        />
        <Feature
          icon={<Shield className="w-5 h-5 text-brand-600" />}
          title="No fake ML"
          text="Both models are trained. Synthetic data is documented and replaceable. No LLM is used as a stand-in."
        />
        <Feature
          icon={<Sparkles className="w-5 h-5 text-brand-600" />}
          title="Persisted history"
          text="Every analysis is stored so you can revisit and compare matches over time."
        />
        <Feature
          icon={<GitBranch className="w-5 h-5 text-brand-600" />}
          title="Docker + tests"
          text="One-line stack startup with docker-compose, pytest suite covering parsers and ML models."
        />
      </section>
    </div>
  );
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-2">{icon}<h3 className="font-semibold">{title}</h3></div>
      <p className="text-sm text-gray-600">{text}</p>
    </div>
  );
}

function ScoreDemoCard() {
  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">Sample match output</div>
      <div className="flex items-center gap-6">
        <div className="w-24 h-24 rounded-full border-8 border-green-500 grid place-items-center text-2xl font-bold text-gray-900">
          85%
        </div>
        <div className="space-y-1">
          <div className="text-sm">
            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mr-2" />
            scikit-learn: <b>82%</b>
          </div>
          <div className="text-sm">
            <span className="inline-block w-2 h-2 bg-purple-500 rounded-full mr-2" />
            PyTorch: <b>87%</b>
          </div>
          <div className="text-xs text-gray-500">Weighted average of both heads.</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 pt-2">
        <div className="rounded-lg border border-green-200 bg-green-50 p-3">
          <div className="text-xs uppercase text-green-700 font-semibold">Matching</div>
          <ul className="mt-1 text-sm text-gray-700 space-y-0.5">
            <li>✓ Python</li>
            <li>✓ SQL</li>
            <li>✓ Machine Learning</li>
          </ul>
        </div>
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-3">
          <div className="text-xs uppercase text-orange-700 font-semibold">Missing</div>
          <ul className="mt-1 text-sm text-gray-700 space-y-0.5">
            <li>⚠ AWS</li>
            <li>⚠ Kubernetes</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
