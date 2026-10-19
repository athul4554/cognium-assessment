import axios from "axios";

// Relative base, next.config.mjs rewrites /api/* to the FastAPI backend
const api = axios.create({ baseURL: "/api/v1" });

export const errorMessage = (error) => {
  const detail = error.response?.data?.detail;
  return typeof detail === "string" ? detail : "Something went wrong, please try again";
};

// Latest assessment for the user, or null if they haven't submitted one yet
export const getRiskAssessment = (userId) =>
  api
    .get("/risk-assessment", { params: { user_id: userId } })
    .then((res) => res.data)
    .catch((error) => {
      if (error.response?.status === 404) return null;
      throw error;
    });

export const createRiskAssessment = (payload) =>
  api.post("/risk-assessment", payload).then((res) => res.data);

export const createAssessmentResult = (userId) =>
  api.post("/assessment-result", { user_id: userId }).then((res) => res.data);

export const getAssessmentResult = (userId) =>
  api.get("/assessment-result", { params: { user_id: userId } }).then((res) => res.data);

// Builds the portfolio for the latest result, returns the stored one if already built
export const createRecommendation = (userId) =>
  api.post("/recommendation", { user_id: userId }).then((res) => res.data);

// Stored portfolio, or null if it hasn't been built yet
export const getRecommendation = (userId) =>
  api
    .get("/recommendation", { params: { user_id: userId } })
    .then((res) => res.data)
    .catch((error) => {
      if (error.response?.status === 404) return null;
      throw error;
    });
