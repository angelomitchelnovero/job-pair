export type ResumeResponse = {
  id: string;
  filename: string;
  full_name?: string | null;
  email?: string | null;
  raw_text: string;
  skills: string[];
  experience: Array<Record<string, unknown>>;
  education: Array<Record<string, unknown>>;
  projects: Array<Record<string, unknown>>;
  certifications: string[];
  sections: Record<string, string>;
  created_at: string;
};

export type JobResponse = {
  id: string;
  title: string;
  company?: string | null;
  description: string;
  skills_required: string[];
  skills_preferred: string[];
  responsibilities: string[];
  experience_years?: number | null;
  education_required?: string | null;
  created_at: string;
};

export type SkillScore = {
  name: string;
  matched: boolean | "required" | "preferred";
};

export type FeatureContribution = {
  feature: string;
  contribution: number;
  direction: string;
};

export type ExperienceAlignment = {
  required_years?: number | null;
  estimated_years?: number | null;
  matched: boolean;
  notes: string;
};

export type EducationAlignment = {
  required: boolean | string | null;
  candidates: string[];
  matched: boolean;
  notes: string;
};

export type MatchResponse = {
  id: string;
  resume_id?: string | null;
  job_id?: string | null;
  // Eagerly-populated context fields. Optional because preview matches
  // (`id="preview"`) have no FKs and never set these. The history page
  // uses job_title / job_company for the sidebar and job_description
  // for the JD preview snippet in the activity card.
  job_title?: string | null;
  job_company?: string | null;
  job_description?: string | null;
  resume_filename?: string | null;
  sklearn_score: number;
  pytorch_score: number;
  final_score: number;
  matching_skills: SkillScore[];
  missing_skills: SkillScore[];
  extra_skills: string[];
  experience_alignment: ExperienceAlignment;
  education_alignment: EducationAlignment;
  recommendations: string[];
  feature_breakdown: FeatureContribution[];
  explanation: string;
  created_at: string;
};

export type ModelPerformanceResponse = {
  id: string;
  model_name: string;
  version: string;
  metrics: Record<string, number>;
  training_samples: number;
  notes?: string | null;
  created_at: string;
};
