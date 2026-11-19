
document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // DOM ELEMENTS
    // ==========================================

    const form = document.getElementById("careerAssessmentForm");
    const submitButton = document.getElementById("generateCareerButton");
    const statusBox = document.getElementById("careerStatus");
    const resultSection = document.getElementById("careerResult");
    const resultContent = document.getElementById("careerResultContent");

    // ==========================================
    // STATUS MESSAGE
    // ==========================================

    function showStatus(message, type = "loading") {
        statusBox.textContent = message;
        statusBox.className = `career-status ${type}`;
    }

    function hideStatus() {
        statusBox.textContent = "";
        statusBox.className = "career-status";
    }

    // ==========================================
    // COLLECT SELECTED CHECKBOX VALUES
    // ==========================================

    function getSelectedValues(name) {
        return Array.from(
            document.querySelectorAll(
                `input[name="${name}"]:checked`
            )
        ).map(input => input.value);
    }

    // ==========================================
    // COLLECT STUDENT ASSESSMENT DATA
    // ==========================================

    function collectAssessmentData() {

        return {
            student_name:
                document.getElementById("studentName").value.trim(),

            branch:
                document.getElementById("studentBranch").value,

            academic_year:
                document.getElementById("studentYear").value,

            cgpa:
                document.getElementById("studentCgpa").value
                    ? Number(document.getElementById("studentCgpa").value)
                    : null,

            interests:
                getSelectedValues("interests"),

            skills:
                getSelectedValues("skills"),

            career_goal:
                document.getElementById("careerGoal").value,

            career_level:
                document.getElementById("careerLevel").value,

            additional_information:
                document.getElementById("careerDescription").value.trim()
        };
    }

    // ==========================================
    // VALIDATE ASSESSMENT DATA
    // ==========================================

    function validateAssessment(data) {

        if (!data.student_name) {
            return "Please enter your name.";
        }

        if (!data.branch) {
            return "Please select your engineering branch.";
        }

        if (!data.academic_year) {
            return "Please select your academic year.";
        }

        if (
            data.cgpa !== null &&
            (data.cgpa < 0 || data.cgpa > 10)
        ) {
            return "CGPA must be between 0 and 10.";
        }

        if (data.interests.length === 0) {
            return "Please select at least one area of interest.";
        }

        if (data.skills.length === 0) {
            return "Please select at least one technical or soft skill.";
        }

        if (!data.career_goal) {
            return "Please select your preferred career goal.";
        }

        return null;
    }

    // ==========================================
    // CREATE RESULT HEADING
    // ==========================================

    function createHeading(text) {
        const heading = document.createElement("h4");
        heading.textContent = text;
        heading.className = "career-result-heading";
        return heading;
    }

    // ==========================================
    // CREATE RESULT CARD
    // ==========================================

    function createResultCard(title, description) {

        const card = document.createElement("div");
        card.className = "career-result-card";

        const heading = document.createElement("h4");
        heading.textContent = title;

        const paragraph = document.createElement("p");
        paragraph.textContent = description;

        card.append(heading, paragraph);

        return card;
    }

    // ==========================================
    // RENDER LIST
    // ==========================================

    function renderList(title, items) {

        const section = document.createElement("div");
        section.className = "career-result-card";

        const heading = document.createElement("h4");
        heading.textContent = title;

        const list = document.createElement("ul");

        (Array.isArray(items) ? items : []).forEach(item => {

            const li = document.createElement("li");

            if (typeof item === "string") {
                li.textContent = item;
            } else if (item && typeof item === "object") {
                li.textContent =
                    item.title ||
                    item.name ||
                    item.skill ||
                    item.description ||
                    JSON.stringify(item);
            }

            list.appendChild(li);
        });

        section.append(heading, list);

        return section;
    }

    // ==========================================
    // RENDER CAREER RECOMMENDATIONS
    // ==========================================

    function renderRecommendations(recommendations) {

        if (!Array.isArray(recommendations) || !recommendations.length) {
            return;
        }

        resultContent.appendChild(
            createHeading("Recommended Career Paths")
        );

        recommendations.forEach(career => {

            if (typeof career === "string") {
                resultContent.appendChild(
                    createResultCard(career, "")
                );
                return;
            }

            const title =
                career.title ||
                career.name ||
                career.career ||
                "Career Recommendation";

            const description =
                career.description ||
                career.reason ||
                career.details ||
                "";

            const card = createResultCard(title, description);

            if (career.suitability) {
                const suitability = document.createElement("p");
                suitability.textContent =
                    `Suitability: ${career.suitability}`;
                card.appendChild(suitability);
            }

            resultContent.appendChild(card);
        });
    }

    // ==========================================
    // RENDER SKILL GAP ANALYSIS
    // ==========================================

    function renderSkillGap(skillGaps) {

        if (!skillGaps) return;

        resultContent.appendChild(
            createHeading("Skill Gap Analysis")
        );

        if (Array.isArray(skillGaps)) {
            resultContent.appendChild(
                renderList("Skills to Develop", skillGaps)
            );
            return;
        }

        if (typeof skillGaps === "object") {

            if (Array.isArray(skillGaps.current_strengths)) {
                resultContent.appendChild(
                    renderList(
                        "Your Current Strengths",
                        skillGaps.current_strengths
                    )
                );
            }

            if (Array.isArray(skillGaps.missing_skills)) {
                resultContent.appendChild(
                    renderList(
                        "Skills You Need to Learn",
                        skillGaps.missing_skills
                    )
                );
            }

            if (Array.isArray(skillGaps.recommended_skills)) {
                resultContent.appendChild(
                    renderList(
                        "Recommended Skills",
                        skillGaps.recommended_skills
                    )
                );
            }
        }
    }

    // ==========================================
    // RENDER LEARNING ROADMAP
    // ==========================================

    function renderRoadmap(roadmap) {

        if (!roadmap) return;

        resultContent.appendChild(
            createHeading("Your Learning Roadmap")
        );

        if (Array.isArray(roadmap)) {

            roadmap.forEach((phase, index) => {

                if (typeof phase === "string") {
                    resultContent.appendChild(
                        createResultCard(
                            `Step ${index + 1}`,
                            phase
                        )
                    );
                    return;
                }

                const title =
                    phase.title ||
                    phase.phase ||
                    `Phase ${index + 1}`;

                const description =
                    phase.description ||
                    phase.tasks ||
                    phase.details ||
                    "";

                const card = createResultCard(title, "");

                const paragraph = document.createElement("p");

                if (Array.isArray(description)) {
                    paragraph.textContent = description.join(", ");
                } else {
                    paragraph.textContent = String(description);
                }

                card.appendChild(paragraph);

                if (phase.duration) {
                    const duration = document.createElement("small");
                    duration.textContent =
                        `Duration: ${phase.duration}`;
                    card.appendChild(duration);
                }

                resultContent.appendChild(card);
            });

            return;
        }

        if (typeof roadmap === "string") {
            resultContent.appendChild(
                createResultCard("Recommended Roadmap", roadmap)
            );
        }
    }

    // ==========================================
    // DISPLAY AI RESPONSE
    // ==========================================

    function displayCareerResults(data) {

        resultContent.replaceChildren();

        const summary =
            data.summary ||
            data.career_analysis ||
            data.analysis ||
            "";

        if (summary) {
            resultContent.appendChild(
                createResultCard(
                    "Career Analysis",
                    typeof summary === "string"
                        ? summary
                        : JSON.stringify(summary)
                )
            );
        }

        renderRecommendations(
            data.recommendations ||
            data.career_recommendations
        );

        renderSkillGap(
            data.skill_gap_analysis ||
            data.skill_gaps
        );

        renderRoadmap(
            data.learning_roadmap ||
            data.roadmap
        );

        if (data.placement_tips) {
            if (Array.isArray(data.placement_tips)) {
                resultContent.appendChild(
                    renderList(
                        "Placement Preparation Tips",
                        data.placement_tips
                    )
                );
            } else {
                resultContent.appendChild(
                    createResultCard(
                        "Placement Preparation Tips",
                        data.placement_tips
                    )
                );
            }
        }

        if (!resultContent.children.length) {
            resultContent.appendChild(
                createResultCard(
                    "Career Guidance",
                    data.message ||
                    "The AI returned a response, but no displayable sections were found."
                )
            );
        }

        resultSection.style.display = "block";

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    // ==========================================
    // SEND DATA TO FLASK BACKEND
    // ==========================================

    async function generateCareerGuidance(data) {

        const response = await fetch(
            "/api/career-guidance/generate",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },

                body: JSON.stringify(data)
            }
        );

        const result = await response.json().catch(() => ({}));

        if (!response.ok || result.success === false) {
            throw new Error(
                result.message ||
                result.error ||
                `Server error: ${response.status}`
            );
        }

        return result;
    }

    // ==========================================
    // FORM SUBMISSION
    // ==========================================

    form.addEventListener("submit", async (event) => {

        event.preventDefault();

        hideStatus();

        const assessmentData = collectAssessmentData();

        const validationError =
            validateAssessment(assessmentData);

        if (validationError) {
            showStatus(validationError, "error");
            return;
        }

        submitButton.disabled = true;

        submitButton.innerHTML =
            '<i class="bi bi-arrow-repeat"></i> Analyzing Your Profile...';

        resultSection.style.display = "none";
        resultContent.replaceChildren();

        showStatus(
            "StudyMate AI is analyzing your profile and preparing your career roadmap. Please wait...",
            "loading"
        );

        try {

            const result =
                await generateCareerGuidance(assessmentData);

            if (result.success === false) {
                throw new Error(
                    result.message || "Career analysis failed."
                );
            }

            displayCareerResults(result);

            showStatus(
                "Your personalized career analysis is ready!",
                "success"
            );

        } catch (error) {

            console.error("Career Guidance Error:", error);

            showStatus(
                error.message ||
                "Unable to generate career guidance. Please try again.",
                "error"
            );

        } finally {

            submitButton.disabled = false;

            submitButton.innerHTML =
                '<i class="bi bi-stars"></i> Generate My Career Roadmap';
        }
    });

});
