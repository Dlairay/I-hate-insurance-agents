/**
 * AI Insurance Broker Frontend Application
 * Handles the complete flow: Profile Upload -> Policy Analysis -> Questionnaire -> Recommendations
 */

class InsuranceApp {
    constructor() {
        this.currentStep = 1;
        this.sessionId = null;
        this.userProfile = null;
        this.policyAnalysis = null;
        this.questionnaireData = null;
        this.currentQuestionIndex = 0;
        this.questions = [];
        this.answers = {};
        this.recommendations = [];
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.showStep(1);
    }

    bindEvents() {
        // Profile upload events
        const profileUpload = document.getElementById('profile-upload');
        const profileUploadArea = document.getElementById('profile-upload-area');
        
        if (profileUpload) {
            profileUpload.addEventListener('change', (e) => this.handleProfileUpload(e));
        }
        
        if (profileUploadArea) {
            profileUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                profileUploadArea.classList.add('drag-over');
            });
            
            profileUploadArea.addEventListener('dragleave', () => {
                profileUploadArea.classList.remove('drag-over');
            });
            
            profileUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                profileUploadArea.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleProfileFile(files[0]);
                }
            });
            
            profileUploadArea.addEventListener('click', () => {
                profileUpload.click();
            });
        }

        // Policy upload events
        const policyUpload = document.getElementById('policy-upload');
        const policyUploadArea = document.getElementById('policy-upload-area');
        
        if (policyUpload) {
            policyUpload.addEventListener('change', (e) => this.handlePolicyUpload(e));
        }
        
        if (policyUploadArea) {
            policyUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                policyUploadArea.classList.add('drag-over');
            });
            
            policyUploadArea.addEventListener('dragleave', () => {
                policyUploadArea.classList.remove('drag-over');
            });
            
            policyUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                policyUploadArea.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handlePolicyFiles(files);
                }
            });
            
            policyUploadArea.addEventListener('click', () => {
                policyUpload.click();
            });
        }

        // Button events
        const startFreshBtn = document.getElementById('start-fresh-btn');
        if (startFreshBtn) {
            startFreshBtn.addEventListener('click', () => this.startFreshQuestionnaire());
        }

        const skipPolicyBtn = document.getElementById('skip-policy-btn');
        if (skipPolicyBtn) {
            skipPolicyBtn.addEventListener('click', () => this.skipPolicyAnalysis());
        }

        const prevQuestionBtn = document.getElementById('prev-question-btn');
        if (prevQuestionBtn) {
            prevQuestionBtn.addEventListener('click', () => this.previousQuestion());
        }

        const nextQuestionBtn = document.getElementById('next-question-btn');
        if (nextQuestionBtn) {
            nextQuestionBtn.addEventListener('click', () => this.nextQuestion());
        }

        // Modal events
        const modal = document.getElementById('plan-detail-modal');
        const closeModalBtn = document.getElementById('close-modal');
        const closeModalFooterBtn = document.getElementById('close-modal-btn');
        
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.closeModal());
        }
        
        if (closeModalFooterBtn) {
            closeModalFooterBtn.addEventListener('click', () => this.closeModal());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeModal();
            });
        }

        // Filter and sort events
        const sortPlans = document.getElementById('sort-plans');
        const filterBudget = document.getElementById('filter-budget');
        
        if (sortPlans) {
            sortPlans.addEventListener('change', () => this.filterAndSortPlans());
        }
        
        if (filterBudget) {
            filterBudget.addEventListener('change', () => this.filterAndSortPlans());
        }
    }

    showStep(stepNumber) {
        console.log(`Showing step ${stepNumber}`);
        
        // Update progress indicator
        document.querySelectorAll('.progress-indicator .step').forEach((step, index) => {
            step.classList.toggle('active', index + 1 <= stepNumber);
            step.classList.toggle('completed', index + 1 < stepNumber);
        });

        // Show/hide step content
        document.querySelectorAll('.step-content').forEach((content, index) => {
            content.classList.toggle('active', index + 1 === stepNumber);
        });

        this.currentStep = stepNumber;
    }

    showLoading(message = 'Processing...') {
        const loadingScreen = document.getElementById('loading-screen');
        const loadingText = document.querySelector('.loading-text');
        
        if (loadingText) {
            loadingText.textContent = message;
        }
        
        if (loadingScreen) {
            loadingScreen.classList.remove('hidden');
        }
    }

    hideLoading() {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            loadingScreen.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = type === 'error' ? 'fas fa-exclamation-triangle' : 
                    type === 'success' ? 'fas fa-check-circle' : 'fas fa-info-circle';
        
        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);

        // Close button
        const closeBtn = notification.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => notification.remove());
        }
    }

    // Profile Upload Handling
    async handleProfileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            await this.handleProfileFile(file);
        }
    }

    async handleProfileFile(file) {
        if (!file.name.endsWith('.json')) {
            this.showNotification('Please select a JSON file', 'error');
            return;
        }

        try {
            this.showLoading('Processing profile...');
            
            const text = await file.text();
            const profileData = JSON.parse(text);
            
            this.userProfile = profileData;
            
            // Start session with profile
            await this.startSessionWithProfile(profileData);
            
            this.hideLoading();
            this.showNotification('Profile uploaded successfully!', 'success');
            this.showStep(2); // Move to policy upload
            
        } catch (error) {
            this.hideLoading();
            console.error('Profile upload error:', error);
            this.showNotification('Failed to process profile file. Please check the format.', 'error');
        }
    }

    async startSessionWithProfile(profileData) {
        try {
            const response = await fetch('/api/start-session-with-profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(profileData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.questionnaireData = data;
            
            console.log('Session started with profile:', data);
        } catch (error) {
            console.error('Failed to start session with profile:', error);
            throw error;
        }
    }

    async startFreshQuestionnaire() {
        try {
            this.showLoading('Starting questionnaire...');
            
            const response = await fetch('/api/start-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.questionnaireData = data;
            
            this.hideLoading();
            this.showStep(3); // Skip policy upload, go straight to questionnaire
            this.initializeQuestionnaire();
            
        } catch (error) {
            this.hideLoading();
            console.error('Failed to start fresh questionnaire:', error);
            this.showNotification('Failed to start questionnaire. Please try again.', 'error');
        }
    }

    // Policy Upload Handling
    async handlePolicyUpload(event) {
        const files = event.target.files;
        if (files.length > 0) {
            await this.handlePolicyFiles(files);
        }
    }

    async handlePolicyFiles(files) {
        try {
            this.showLoading('Analyzing policy documents...');
            
            // Process each file
            const analyses = [];
            for (const file of files) {
                const analysis = await this.analyzePolicyFile(file);
                analyses.push(analysis);
            }

            this.policyAnalysis = analyses;
            this.displayPolicyAnalysis(analyses);
            
            this.hideLoading();
            this.showNotification('Policy documents analyzed successfully!', 'success');
            
            // Auto-advance after 3 seconds
            setTimeout(() => {
                this.showStep(3);
                this.initializeQuestionnaire();
            }, 3000);
            
        } catch (error) {
            this.hideLoading();
            console.error('Policy analysis error:', error);
            this.showNotification('Failed to analyze policy documents.', 'error');
        }
    }

    async analyzePolicyFile(file) {
        const formData = new FormData();
        formData.append('policy_file', file);

        const response = await fetch('/api/upload-policy', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    displayPolicyAnalysis(analyses) {
        const resultsContainer = document.getElementById('policy-analysis-results');
        const contentContainer = document.getElementById('policy-analysis-content');
        
        if (!resultsContainer || !contentContainer) return;

        let content = '';
        analyses.forEach((analysis, index) => {
            const recommendation = analysis.recommendation || {};
            const policyAssessment = analysis.existing_policy_analysis || {};
            
            content += `
                <div class="policy-analysis-item">
                    <div class="policy-file-info">
                        <i class="fas fa-file-pdf"></i>
                        <span>${analysis.filename}</span>
                        <span class="confidence-score">Confidence: ${Math.round((analysis.extraction_confidence || 0.3) * 100)}%</span>
                    </div>
                    <div class="policy-assessment">
                        <h4>Analysis Results:</h4>
                        <p><strong>Coverage Adequacy:</strong> ${this.formatCoverageAdequacy(policyAssessment.coverage_adequacy)}</p>
                        <p><strong>Primary Recommendation:</strong> ${policyAssessment.primary_action || 'Continue current coverage'}</p>
                        <p><strong>Reasoning:</strong> ${policyAssessment.analysis_reasoning || recommendation.message || 'Unable to perform detailed analysis'}</p>
                        ${policyAssessment.potential_monthly_savings > 0 ? 
                            `<p class="savings"><strong>Potential Savings:</strong> $${policyAssessment.potential_monthly_savings}/month</p>` : ''}
                    </div>
                    ${policyAssessment.specific_actions && policyAssessment.specific_actions.length > 0 ? `
                        <div class="action-items">
                            <h4>Recommended Actions:</h4>
                            <ul>
                                ${policyAssessment.specific_actions.slice(0, 3).map(action => `<li>${action}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        });

        contentContainer.innerHTML = content;
        resultsContainer.style.display = 'block';
    }

    formatCoverageAdequacy(adequacy) {
        const mapping = {
            'under_insured': 'Under-insured',
            'adequately_insured': 'Adequately insured',
            'over_insured': 'Over-insured',
            'no_coverage': 'No coverage',
            'unknown': 'Unknown'
        };
        return mapping[adequacy] || adequacy || 'Unknown';
    }

    skipPolicyAnalysis() {
        this.showStep(3);
        this.initializeQuestionnaire();
    }

    // Questionnaire Handling
    async initializeQuestionnaire() {
        try {
            if (!this.sessionId) {
                // Start a new session if none exists
                await this.startFreshQuestionnaire();
                return;
            }

            // If we already have questionnaire data from profile upload, use it
            if (this.questionnaireData && this.questionnaireData.current_question) {
                this.displayQuestion(this.questionnaireData.current_question);
                this.updateQuestionProgress(this.questionnaireData.progress);
                this.updateNavigationButtons(this.questionnaireData.progress);
            } else {
                // Get the current question from the session
                await this.getCurrentQuestion();
            }
            
        } catch (error) {
            console.error('Failed to initialize questionnaire:', error);
            this.showNotification('Failed to load questionnaire.', 'error');
        }
    }

    async getCurrentQuestion() {
        try {
            const response = await fetch(`/api/session/${this.sessionId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.current_question) {
                this.displayQuestion(data.current_question);
                this.updateQuestionProgress(data.progress);
                this.updateNavigationButtons(data.progress);
            } else {
                // Questionnaire completed
                this.handleQuestionnaireComplete(data);
            }
            
        } catch (error) {
            console.error('Failed to get current question:', error);
            throw error;
        }
    }

    displayQuestion(question) {
        const container = document.getElementById('question-container');
        if (!container) return;

        let questionHtml = `
            <div class="question">
                <h3>${question.question_text}</h3>
                ${question.help_text ? `<p class="help-text">${question.help_text}</p>` : ''}
                <div class="question-input">
        `;

        switch (question.question_type) {
            case 'text':
                questionHtml += `
                    <input type="text" 
                           id="question-input" 
                           class="text-input" 
                           placeholder="Enter your answer"
                           ${question.required ? 'required' : ''}>
                `;
                break;
            
            case 'number':
                questionHtml += `
                    <input type="number" 
                           id="question-input" 
                           class="text-input" 
                           placeholder="Enter a number"
                           ${question.required ? 'required' : ''}>
                `;
                break;
            
            case 'mcq_single':
                questionHtml += '<div class="radio-group">';
                question.options.forEach((option, index) => {
                    questionHtml += `
                        <label class="radio-option">
                            <input type="radio" 
                                   name="question-answer" 
                                   value="${option.value}" 
                                   id="option-${index}">
                            <span class="radio-label">${option.label}</span>
                            ${option.description ? `<span class="option-description">${option.description}</span>` : ''}
                        </label>
                    `;
                });
                questionHtml += '</div>';
                break;
            
            case 'mcq_multiple':
                questionHtml += '<div class="checkbox-group">';
                question.options.forEach((option, index) => {
                    questionHtml += `
                        <label class="checkbox-option">
                            <input type="checkbox" 
                                   name="question-answer" 
                                   value="${option.value}" 
                                   id="option-${index}">
                            <span class="checkbox-label">${option.label}</span>
                            ${option.description ? `<span class="option-description">${option.description}</span>` : ''}
                        </label>
                    `;
                });
                questionHtml += '</div>';
                break;
        }

        questionHtml += `
                </div>
                <div class="question-help">
                    <button class="btn-help" id="get-help-btn">
                        <i class="fas fa-question-circle"></i>
                        Need Help?
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = questionHtml;

        // Bind input events
        this.bindQuestionEvents();
    }

    bindQuestionEvents() {
        const inputs = document.querySelectorAll('input[name="question-answer"], #question-input');
        const nextBtn = document.getElementById('next-question-btn');
        
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                const hasAnswer = this.getCurrentAnswer() !== null;
                if (nextBtn) {
                    nextBtn.disabled = !hasAnswer;
                }
            });
        });

        // Help button
        const helpBtn = document.getElementById('get-help-btn');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => this.showQuestionHelp());
        }
    }

    getCurrentAnswer() {
        const textInput = document.getElementById('question-input');
        if (textInput) {
            return textInput.value.trim() || null;
        }

        const radioInputs = document.querySelectorAll('input[name="question-answer"]:checked');
        if (radioInputs.length > 0) {
            return radioInputs[0].value;
        }

        const checkboxInputs = document.querySelectorAll('input[name="question-answer"]:checked');
        if (checkboxInputs.length > 0) {
            return Array.from(checkboxInputs).map(input => input.value);
        }

        return null;
    }

    async nextQuestion() {
        const answer = this.getCurrentAnswer();
        if (!answer) {
            this.showNotification('Please answer the question before continuing.', 'error');
            return;
        }

        try {
            this.showLoading('Processing answer...');
            
            const response = await fetch(`/api/session/${this.sessionId}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    answer: answer,
                    needs_help: false
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.hideLoading();

            if (data.completed) {
                // Questionnaire completed, show recommendations
                this.handleQuestionnaireComplete(data);
            } else {
                // Show next question
                if (data.next_question) {
                    this.displayQuestion(data.next_question);
                    this.updateQuestionProgress(data.progress);
                    this.updateNavigationButtons(data.progress);
                }
            }

        } catch (error) {
            this.hideLoading();
            console.error('Failed to submit answer:', error);
            this.showNotification('Failed to submit answer. Please try again.', 'error');
        }
    }

    async previousQuestion() {
        if (!this.sessionId) {
            this.showNotification('No active session', 'error');
            return;
        }

        try {
            this.showLoading('Going back...');
            
            const response = await fetch(`/api/session/${this.sessionId}/back`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            this.hideLoading();

            if (!response.ok) {
                const errorData = await response.json();
                this.showNotification(errorData.detail || 'Cannot go back further', 'info');
                return;
            }

            const data = await response.json();
            
            if (data.success && data.current_question) {
                // Display the previous question
                this.displayQuestion(data.current_question);
                this.updateQuestionProgress(data.progress);
                this.updateNavigationButtons(data.progress);
                this.showNotification('Went back to previous question', 'success');
            } else {
                this.showNotification('No previous question available', 'info');
            }

        } catch (error) {
            this.hideLoading();
            console.error('Failed to go back:', error);
            this.showNotification('Failed to go back. Please try again.', 'error');
        }
    }

    updateNavigationButtons(progress) {
        const prevBtn = document.getElementById('prev-question-btn');
        const nextBtn = document.getElementById('next-question-btn');
        
        if (prevBtn) {
            // Enable back button if not on first question
            prevBtn.disabled = progress.current <= 1;
        }
        
        // Next button state is handled by the question input events
    }

    updateQuestionProgress(progress) {
        const current = progress.current;
        const total = progress.total;
        const percentage = (current / total) * 100;

        const progressBar = document.getElementById('questionnaire-progress');
        const currentSpan = document.getElementById('current-question');
        const totalSpan = document.getElementById('total-questions');

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }

        if (currentSpan) {
            currentSpan.textContent = current;
        }

        if (totalSpan) {
            totalSpan.textContent = total;
        }
    }

    async showQuestionHelp() {
        // Use a simple alert instead of prompt for now
        this.showAlert('AI help feature is temporarily unavailable. Please answer based on your best knowledge.', 'info');
        return;
        
        if (!this.sessionId) {
            this.showNotification('Please start a session first', 'error');
            return;
        }
        
        try {
            this.showLoading('Getting AI assistance...');
            
            const response = await fetch(`/api/session/${this.sessionId}/get-help`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    description: description.trim()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.hideLoading();
            
            console.log('AI Help Response:', data);  // Debug log
            
            // Auto-apply AI suggestion without popup
            if (data && data.suggested_answer) {
                // Log detailed AI response for debugging
                console.log('AI Suggestion Details:', {
                    answer: data.suggested_answer,
                    explanation: data.explanation || 'Based on your description',
                    confidence: Math.round((data.confidence || 0.8) * 100) + '%',
                    timestamp: new Date().toISOString()
                });
                
                // Automatically set the answer in the form
                this.setQuestionAnswer(data.suggested_answer);
                
                // Show brief success notification instead of popup
                this.showNotification(`AI selected: ${data.suggested_answer}`, 'success');
            } else {
                this.showNotification('Unable to provide a suggestion. Please try rephrasing.', 'info');
            }
            
        } catch (error) {
            this.hideLoading();
            console.error('AI help error:', error);
            this.showNotification('Failed to get AI assistance. Please try again.', 'error');
        }
    }
    
    setQuestionAnswer(answer) {
        // Set the answer based on question type
        const textInput = document.getElementById('question-input');
        if (textInput) {
            textInput.value = answer;
            textInput.dispatchEvent(new Event('change'));
            return;
        }
        
        // For radio buttons
        const radioInputs = document.querySelectorAll('input[name="question-answer"]');
        radioInputs.forEach(input => {
            if (input.value === answer) {
                input.checked = true;
                input.dispatchEvent(new Event('change'));
            }
        });
        
        // Enable the next button if answer is set
        const nextBtn = document.getElementById('next-question-btn');
        if (nextBtn) {
            nextBtn.disabled = false;
        }
    }

    // Recommendations Handling
    async handleQuestionnaireComplete(data) {
        console.log('Questionnaire completed:', data);
        
        this.showLoading('Getting your personalized recommendations...');
        
        try {
            // The backend should have returned recommendations in the data
            if (data.insurance_response) {
                await this.processRecommendations(data.insurance_response);
            } else {
                throw new Error('No recommendations received');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Failed to process recommendations:', error);
            this.showNotification('Failed to get recommendations. Please try again.', 'error');
        }
    }

    async processRecommendations(insuranceResponse) {
        try {
            // Handle both MVP and legacy response formats
            let plans = [];
            
            if (insuranceResponse.new_quotes) {
                // MVP format
                const quotes = insuranceResponse.new_quotes;
                plans = quotes.parsed_cards || quotes.quotes || [];
            } else if (insuranceResponse.quotes) {
                // Legacy format
                plans = insuranceResponse.parsed_cards || insuranceResponse.quotes || [];
            }

            this.recommendations = plans;
            this.displayRecommendations(plans);
            
            this.hideLoading();
            this.showStep(4); // Show recommendations
            
        } catch (error) {
            console.error('Failed to process recommendations:', error);
            throw error;
        }
    }

    displayRecommendations(plans) {
        const container = document.getElementById('plans-container');
        if (!container || !plans.length) {
            if (container) {
                container.innerHTML = `
                    <div class="no-plans">
                        <i class="fas fa-search"></i>
                        <h3>No plans found</h3>
                        <p>We couldn't find any plans matching your criteria. Please try adjusting your preferences.</p>
                    </div>
                `;
            }
            return;
        }

        let plansHtml = '';
        plans.forEach((plan, index) => {
            plansHtml += this.createPlanCard(plan, index);
        });

        container.innerHTML = plansHtml;

        // Bind card click events
        this.bindPlanCardEvents();
    }

    createPlanCard(plan, index) {
        // Handle different data formats
        const companyName = plan.company_name || 'Insurance Company';
        const planName = plan.plan_name || plan.product_name || 'Insurance Plan';
        const monthlyCost = plan.monthly_cost || `$${plan.total_monthly_premium || plan.monthly_premium || 0}/month`;
        const coverageAmount = plan.coverage_amount || `$${plan.coverage_amount || 0}`;
        const keyBenefits = plan.key_benefits || plan.key_features || ['Coverage included'];
        
        // Scoring data (if available)
        const scores = plan.scores || {};
        const overallScore = scores.overall_score || plan.value_score || 75;
        const affordabilityScore = scores.affordability_score || 75;
        const claimsEaseScore = scores.ease_of_claims_score || 75;
        const coverageRatioScore = scores.coverage_ratio_score || 75;
        
        // Status badges
        let badges = [];
        if (plan.recommended || index === 0) badges.push('Recommended');
        if (plan.best_value || overallScore >= 90) badges.push('Best Value');
        if (plan.fastest_approval || plan.instant_approval) badges.push('Fast Approval');
        
        const badgeHtml = badges.map(badge => `<span class="badge badge-${badge.toLowerCase().replace(' ', '-')}">${badge}</span>`).join('');

        return `
            <div class="plan-card ${plan.recommended || index === 0 ? 'recommended' : ''}" data-plan-index="${index}">
                <div class="plan-header">
                    <div class="company-info">
                        <h3 class="company-name">${companyName}</h3>
                        <h4 class="plan-name">${planName}</h4>
                        ${plan.company_rating ? `<div class="company-rating">
                            <i class="fas fa-star"></i>
                            <span>${plan.company_rating}/5</span>
                        </div>` : ''}
                    </div>
                    <div class="plan-cost">
                        <span class="monthly-cost">${monthlyCost}</span>
                        <span class="coverage-amount">${coverageAmount} coverage</span>
                    </div>
                </div>
                
                <div class="plan-badges">
                    ${badgeHtml}
                </div>
                
                <div class="plan-scores">
                    <div class="score-item">
                        <span class="score-label">Overall Score</span>
                        <div class="score-bar">
                            <div class="score-fill" style="width: ${overallScore}%"></div>
                            <span class="score-value">${overallScore}/100</span>
                        </div>
                    </div>
                    <div class="score-grid">
                        <div class="score-item-small">
                            <span class="score-label">Affordability</span>
                            <span class="score-value-small">${affordabilityScore}/100</span>
                        </div>
                        <div class="score-item-small">
                            <span class="score-label">Claims Ease</span>
                            <span class="score-value-small">${claimsEaseScore}/100</span>
                        </div>
                        <div class="score-item-small">
                            <span class="score-label">Coverage Value</span>
                            <span class="score-value-small">${coverageRatioScore}/100</span>
                        </div>
                    </div>
                </div>
                
                <div class="plan-benefits">
                    <h5>Key Benefits:</h5>
                    <ul>
                        ${keyBenefits.slice(0, 4).map(benefit => `<li>${benefit}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="plan-actions">
                    <button class="btn-secondary view-details-btn" data-plan-index="${index}">
                        View Details
                        <i class="fas fa-arrow-right"></i>
                    </button>
                    ${this.isUserLoggedIn() ? 
                        `<button class="btn-primary purchase-btn" data-plan-index="${index}">
                            Purchase Policy
                            <i class="fas fa-shopping-cart"></i>
                        </button>` :
                        `<button class="btn-primary get-quote-btn" data-plan-index="${index}">
                            Get Quote
                            <i class="fas fa-external-link-alt"></i>
                        </button>`
                    }
                </div>
            </div>
        `;
    }

    bindPlanCardEvents() {
        // View details buttons
        document.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const planIndex = parseInt(btn.dataset.planIndex);
                this.showPlanDetails(planIndex);
            });
        });

        // Get quote buttons
        document.querySelectorAll('.get-quote-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const planIndex = parseInt(btn.dataset.planIndex);
                this.getQuote(planIndex);
            });
        });

        // Purchase buttons (for logged-in users)
        document.querySelectorAll('.purchase-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const planIndex = parseInt(btn.dataset.planIndex);
                this.purchasePolicy(planIndex);
            });
        });

        // Card click to view details
        document.querySelectorAll('.plan-card').forEach(card => {
            card.addEventListener('click', () => {
                const planIndex = parseInt(card.dataset.planIndex);
                this.showPlanDetails(planIndex);
            });
        });
    }

    showPlanDetails(planIndex) {
        const plan = this.recommendations[planIndex];
        if (!plan) return;

        const modal = document.getElementById('plan-detail-modal');
        const modalPlanName = document.getElementById('modal-plan-name');
        const modalBody = document.getElementById('modal-body');

        if (!modal || !modalPlanName || !modalBody) return;

        modalPlanName.textContent = `${plan.company_name} - ${plan.plan_name}`;

        const scores = plan.scores || {};
        const detailsHtml = `
            <div class="plan-detail-content">
                <div class="detail-section">
                    <h4>Coverage Information</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Coverage Amount:</span>
                            <span class="detail-value">${plan.coverage_amount || 'Not specified'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Monthly Premium:</span>
                            <span class="detail-value">${plan.monthly_cost}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Deductible:</span>
                            <span class="detail-value">${plan.deductible || 'Not specified'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Waiting Period:</span>
                            <span class="detail-value">${plan.waiting_period || 'None'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Scoring Breakdown</h4>
                    <div class="score-details">
                        <div class="score-detail-item">
                            <span class="score-label">Affordability Score</span>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${scores.affordability_score || 75}%"></div>
                            </div>
                            <span class="score-value">${scores.affordability_score || 75}/100</span>
                        </div>
                        <div class="score-detail-item">
                            <span class="score-label">Claims Ease Score</span>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${scores.ease_of_claims_score || 75}%"></div>
                            </div>
                            <span class="score-value">${scores.ease_of_claims_score || 75}/100</span>
                        </div>
                        <div class="score-detail-item">
                            <span class="score-label">Coverage Ratio Score</span>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${scores.coverage_ratio_score || 75}%"></div>
                            </div>
                            <span class="score-value">${scores.coverage_ratio_score || 75}/100</span>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Benefits & Features</h4>
                    <ul class="benefits-list">
                        ${(plan.key_benefits || plan.key_features || []).map(benefit => `<li>${benefit}</li>`).join('')}
                    </ul>
                </div>
                
                ${plan.riders_included && plan.riders_included.length > 0 ? `
                    <div class="detail-section">
                        <h4>Included Riders</h4>
                        <ul class="benefits-list">
                            ${plan.riders_included.map(rider => `<li>${rider}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${plan.exclusions && plan.exclusions.length > 0 ? `
                    <div class="detail-section">
                        <h4>Exclusions</h4>
                        <ul class="exclusions-list">
                            ${plan.exclusions.map(exclusion => `<li>${exclusion}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${scores.value_proposition ? `
                    <div class="detail-section">
                        <h4>Why This Plan?</h4>
                        <p class="value-proposition">${scores.value_proposition}</p>
                    </div>
                ` : ''}
            </div>
        `;

        modalBody.innerHTML = detailsHtml;
        modal.style.display = 'flex';

        // Update get quote button in modal
        const getQuoteBtn = document.getElementById('get-quote-btn');
        if (getQuoteBtn) {
            getQuoteBtn.onclick = () => this.getQuote(planIndex);
        }
    }

    closeModal() {
        const modal = document.getElementById('plan-detail-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    getQuote(planIndex) {
        const plan = this.recommendations[planIndex];
        if (!plan) return;

        // For now, just show a notification
        // In a real app, this would redirect to the insurance company's website
        this.showNotification(`Redirecting to get a quote from ${plan.company_name}...`, 'success');
        
        // Simulate redirect delay
        setTimeout(() => {
            window.open('#', '_blank'); // Replace with actual insurance company URL
        }, 1500);
    }

    isUserLoggedIn() {
        // Check if user is logged in by looking for user data in localStorage
        const userData = localStorage.getItem('user_data');
        return userData !== null;
    }

    async purchasePolicy(planIndex) {
        const plan = this.recommendations[planIndex];
        if (!plan) return;

        const userData = localStorage.getItem('user_data');
        if (!userData) {
            this.showNotification('Please log in to purchase a policy', 'error');
            return;
        }

        const user = JSON.parse(userData);

        // Show confirmation dialog
        // Remove confirmation popup - proceed directly with purchase

        try {
            // Show loading state
            this.showNotification('Processing your purchase...', 'success');

            const purchaseData = {
                user_id: user.user_id,
                plan_id: plan.plan_id || plan.id || `PLAN_${Date.now()}`,
                quote_data: {
                    company_name: plan.company_name,
                    plan_name: plan.plan_name || plan.product_name,
                    coverage_amount: plan.coverage_amount,
                    monthly_premium: plan.monthly_cost ? parseFloat(plan.monthly_cost.replace(/[$,]/g, '')) : plan.total_monthly_premium || plan.monthly_premium || 0,
                    annual_premium: plan.annual_cost ? parseFloat(plan.annual_cost.replace(/[$,]/g, '')) : plan.total_annual_premium || plan.annual_premium || 0
                },
                session_id: this.sessionId
            };

            const response = await fetch('/api/policies/purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(purchaseData)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(`Policy purchased successfully! Policy #${result.policy_number}`, 'success');
                
                // Redirect to dashboard after successful purchase
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            } else {
                this.showNotification(result.message || 'Failed to purchase policy', 'error');
            }
        } catch (error) {
            console.error('Policy purchase error:', error);
            this.showNotification('Failed to purchase policy. Please try again.', 'error');
        }
    }

    filterAndSortPlans() {
        const sortBy = document.getElementById('sort-plans')?.value || 'overall_score';
        const filterBudget = document.getElementById('filter-budget')?.value || 'all';
        
        let filteredPlans = [...this.recommendations];

        // Apply budget filter
        if (filterBudget !== 'all') {
            filteredPlans = filteredPlans.filter(plan => {
                const monthlyCost = this.extractMonthlyCost(plan.monthly_cost);
                switch (filterBudget) {
                    case 'under_100': return monthlyCost < 100;
                    case '100_200': return monthlyCost >= 100 && monthlyCost <= 200;
                    case '200_400': return monthlyCost >= 200 && monthlyCost <= 400;
                    default: return true;
                }
            });
        }

        // Apply sorting
        filteredPlans.sort((a, b) => {
            const scoreA = (a.scores && a.scores[sortBy]) || a.value_score || 75;
            const scoreB = (b.scores && b.scores[sortBy]) || b.value_score || 75;
            return scoreB - scoreA; // Descending order
        });

        this.displayRecommendations(filteredPlans);
    }

    extractMonthlyCost(costString) {
        const match = costString.match(/\$(\d+)/);
        return match ? parseInt(match[1]) : 0;
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.insuranceApp = new InsuranceApp();
    initializeNavigation();
});

// Navigation initialization
function initializeNavigation() {
    const userData = localStorage.getItem('user_data');
    const userNav = document.getElementById('user-nav');
    const guestNav = document.getElementById('guest-nav');
    const userGreeting = document.getElementById('user-greeting');
    const logoutBtn = document.getElementById('logout-btn');
    
    if (userData) {
        // User is logged in
        const user = JSON.parse(userData);
        
        if (userGreeting) {
            userGreeting.textContent = `Hello, ${user.full_name}`;
        }
        
        if (userNav) userNav.style.display = 'flex';
        if (guestNav) guestNav.style.display = 'none';
        
        // Add logout handler
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                localStorage.removeItem('user_data');
                localStorage.removeItem('selected_policy_id');
                window.location.href = '/login';
            });
        }
    } else {
        // User is not logged in
        if (userNav) userNav.style.display = 'none';
        if (guestNav) guestNav.style.display = 'flex';
    }
}