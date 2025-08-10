// Insurance Questionnaire JavaScript
class QuestionnaireApp {
    constructor() {
        this.sessionId = null;
        this.currentQuestion = null;
        this.selectedAnswer = null;
        this.currentProgress = { current: 0, total: 0 };
        
        this.init();
    }

    init() {
        this.bindEvents();
        console.log('Questionnaire app initialized');
    }

    bindEvents() {
        // Start button
        document.getElementById('start-btn').addEventListener('click', () => {
            this.startQuestionnaire();
        });

        // Navigation buttons
        document.getElementById('next-btn').addEventListener('click', () => {
            this.submitAnswer();
        });

        document.getElementById('back-btn').addEventListener('click', () => {
            this.goBack();
        });

        // Help system
        document.getElementById('need-help-btn').addEventListener('click', () => {
            this.showHelpSection();
        });

        document.getElementById('cancel-help-btn').addEventListener('click', () => {
            this.hideHelpSection();
        });

        document.getElementById('get-help-btn').addEventListener('click', () => {
            this.getAIHelp();
        });

        // Results actions
        document.getElementById('start-over-btn').addEventListener('click', () => {
            this.startOver();
        });

        document.getElementById('contact-agent-btn').addEventListener('click', () => {
            this.contactAgent();
        });

        // Profile upload
        document.getElementById('profile-upload').addEventListener('change', (e) => {
            this.handleProfileUpload(e);
        });
    }

    async startQuestionnaire() {
        try {
            this.showLoading('Starting questionnaire...');
            
            const response = await fetch('/api/start-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.currentProgress = data.progress;
            
            this.hideWelcomeScreen();
            this.showQuestionScreen();
            this.displayQuestion(data.current_question);
            this.updateProgress();

        } catch (error) {
            console.error('Error starting questionnaire:', error);
            this.showError('Failed to start questionnaire. Please try again.');
        }
    }

    displayQuestion(question) {
        this.currentQuestion = question;
        this.selectedAnswer = null;
        
        // Update question text and help
        document.getElementById('question-text').textContent = question.question_text;
        document.getElementById('question-category').textContent = question.category.toUpperCase();
        
        const helpElement = document.getElementById('question-help');
        if (question.help_text) {
            helpElement.textContent = question.help_text;
            helpElement.style.display = 'block';
        } else {
            helpElement.style.display = 'none';
        }

        // Clear previous content
        const contentElement = document.getElementById('question-content');
        contentElement.innerHTML = '';

        // Render question based on type
        if (question.question_type === 'mcq_single') {
            this.renderSingleChoice(contentElement, question);
        } else if (question.question_type === 'mcq_multiple') {
            this.renderMultipleChoice(contentElement, question);
        } else if (question.question_type === 'text') {
            this.renderTextInput(contentElement, question);
        } else if (question.question_type === 'date') {
            this.renderDateInput(contentElement, question);
        } else if (question.question_type === 'number') {
            this.renderNumberInput(contentElement, question);
        }

        // Reset help section
        this.hideHelpSection();
        this.hideAISuggestion();
        
        // Update next button
        this.updateNextButton();
    }

    renderSingleChoice(container, question) {
        const optionsHtml = question.options.map((option, index) => `
            <div class="option-card" data-value="${option.value}" onclick="app.selectSingleOption('${option.value}')">
                <div class="d-flex align-items-center">
                    <i class="fas fa-circle option-radio me-3"></i>
                    <div class="flex-grow-1">
                        <div class="fw-medium">${option.label}</div>
                        ${option.description ? `<div class="option-description">${option.description}</div>` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = optionsHtml;
    }

    renderMultipleChoice(container, question) {
        const optionsHtml = question.options.map((option, index) => `
            <div class="option-card" data-value="${option.value}" onclick="app.toggleMultipleOption('${option.value}')">
                <div class="d-flex align-items-center">
                    <i class="fas fa-square option-radio me-3"></i>
                    <div class="flex-grow-1">
                        <div class="fw-medium">${option.label}</div>
                        ${option.description ? `<div class="option-description">${option.description}</div>` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = optionsHtml;
    }

    renderTextInput(container, question) {
        container.innerHTML = `
            <div class="mb-3">
                <input type="text" class="form-control form-control-lg" id="text-input" 
                       placeholder="Enter your answer..." onchange="app.selectTextAnswer(this.value)">
            </div>
        `;
    }

    renderDateInput(container, question) {
        container.innerHTML = `
            <div class="mb-3">
                <input type="date" class="form-control form-control-lg" id="date-input" 
                       onchange="app.selectTextAnswer(this.value)">
            </div>
        `;
    }

    renderNumberInput(container, question) {
        container.innerHTML = `
            <div class="mb-3">
                <input type="number" class="form-control form-control-lg" id="number-input" 
                       placeholder="Enter a number..." onchange="app.selectTextAnswer(this.value)">
            </div>
        `;
    }

    selectSingleOption(value) {
        // Clear previous selections
        document.querySelectorAll('.option-card').forEach(card => {
            card.classList.remove('selected');
            card.querySelector('.option-radio').classList.remove('fa-dot-circle');
            card.querySelector('.option-radio').classList.add('fa-circle');
        });

        // Select new option
        const selectedCard = document.querySelector(`[data-value="${value}"]`);
        selectedCard.classList.add('selected');
        selectedCard.querySelector('.option-radio').classList.remove('fa-circle');
        selectedCard.querySelector('.option-radio').classList.add('fa-dot-circle');

        this.selectedAnswer = value;
        this.updateNextButton();
    }

    toggleMultipleOption(value) {
        const card = document.querySelector(`[data-value="${value}"]`);
        const isSelected = card.classList.contains('selected');

        if (!this.selectedAnswer) {
            this.selectedAnswer = [];
        }

        if (isSelected) {
            // Deselect
            card.classList.remove('selected');
            card.querySelector('.option-radio').classList.remove('fa-check-square');
            card.querySelector('.option-radio').classList.add('fa-square');
            
            const index = this.selectedAnswer.indexOf(value);
            if (index > -1) {
                this.selectedAnswer.splice(index, 1);
            }
        } else {
            // Select
            card.classList.add('selected');
            card.querySelector('.option-radio').classList.remove('fa-square');
            card.querySelector('.option-radio').classList.add('fa-check-square');
            
            if (!this.selectedAnswer.includes(value)) {
                this.selectedAnswer.push(value);
            }
        }

        this.updateNextButton();
    }

    selectTextAnswer(value) {
        this.selectedAnswer = value;
        this.updateNextButton();
    }

    updateNextButton() {
        const nextBtn = document.getElementById('next-btn');
        const isAnswered = this.selectedAnswer !== null && this.selectedAnswer !== '' && 
                          (Array.isArray(this.selectedAnswer) ? this.selectedAnswer.length > 0 : true);
        
        nextBtn.disabled = !isAnswered;
        
        // Update button text based on progress
        const nextBtnText = document.getElementById('next-btn-text');
        if (this.currentProgress.current >= this.currentProgress.total) {
            nextBtnText.textContent = 'Get Quotes';
        } else {
            nextBtnText.textContent = 'Next';
        }
    }

    async submitAnswer() {
        if (!this.selectedAnswer) return;

        try {
            this.showLoading('Processing answer...');

            const needsHelp = document.getElementById('help-description').value.trim() !== '';
            const helpDescription = needsHelp ? document.getElementById('help-description').value : null;

            const response = await fetch(`/api/session/${this.sessionId}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answer: this.selectedAnswer,
                    needs_help: needsHelp,
                    help_description: helpDescription
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.completed) {
                // Show results
                this.showResults(data.insurance_response);
            } else {
                // Show next question
                this.currentProgress = data.progress;
                this.updateProgress();
                this.displayQuestion(data.next_question);
            }

        } catch (error) {
            console.error('Error submitting answer:', error);
            this.showError('Failed to submit answer. Please try again.');
        }
    }

    async createSessionForHelp() {
        try {
            const response = await fetch('/api/start-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.currentQuestion = data.current_question;
            this.currentProgress = data.progress;
            console.log('Session created for AI help:', this.sessionId);
        } catch (error) {
            console.error('Error creating session for help:', error);
            throw error;
        }
    }

    async getAIHelp() {
        const description = document.getElementById('help-description').value.trim();
        if (!description) {
            alert('Please describe your situation first.');
            return;
        }

        console.log('=== AI Help Debug ===');
        console.log('Description:', description);
        console.log('Current session ID:', this.sessionId);

        try {
            document.getElementById('get-help-btn').innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Getting help...';

            // Start a session if we don't have one yet (just for AI help, don't change UI)
            if (!this.sessionId) {
                console.log('No session exists, creating one for AI help...');
                await this.createSessionForHelp();
                console.log('Session created:', this.sessionId);
            }

            const url = `/api/session/${this.sessionId}/get-help`;
            const body = JSON.stringify({ description: description });
            
            console.log('Making request to:', url);
            console.log('Request body:', body);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: body
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);

            if (!response.ok) {
                const errorText = await response.text();
                console.log('Error response text:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }

            const data = await response.json();
            console.log('AI Help response data:', data);
            
            // Always show the AI suggestion, regardless of whether we're in questionnaire or not
            this.showAISuggestion(data.suggested_answer, data.explanation);

        } catch (error) {
            console.error('=== AI Help Error ===');
            console.error('Error details:', error);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);
            
            // Show a more helpful error message that includes the actual error
            alert(`Failed to get AI help: ${error.message}\n\nCheck browser console for details.`);
        } finally {
            document.getElementById('get-help-btn').innerHTML = '<i class="fas fa-magic me-1"></i>Get AI Suggestion';
        }
    }

    showAISuggestion(answer, explanation) {
        console.log('=== showAISuggestion called ===');
        console.log('Answer:', answer);
        console.log('Explanation:', explanation);
        console.log('Current question:', this.currentQuestion);
        console.log('Welcome screen display:', document.getElementById('welcome-screen').style.display);
        
        // If we're still on welcome screen, provide more context
        if (!this.currentQuestion || document.getElementById('welcome-screen').style.display !== 'none') {
            console.log('Showing AI suggestion for welcome screen');
            document.getElementById('ai-suggestion-text').textContent = 
                `Based on your description, I suggest starting with: "${answer}"`;
            document.getElementById('ai-explanation').textContent = 
                explanation + " When you're ready, click 'Start Questionnaire' to begin with personalized questions.";
        } else {
            console.log('Showing AI suggestion for question screen');
            // Normal flow when in questionnaire
            document.getElementById('ai-suggestion-text').textContent = 
                `I recommend selecting: "${this.getOptionLabel(answer)}"`;
            document.getElementById('ai-explanation').textContent = explanation;
            
            // Auto-select the suggested answer
            if (this.currentQuestion.question_type === 'mcq_single') {
                this.selectSingleOption(answer);
            } else if (this.currentQuestion.question_type === 'text' || 
                       this.currentQuestion.question_type === 'date' || 
                       this.currentQuestion.question_type === 'number') {
                const input = document.querySelector('#text-input, #date-input, #number-input');
                if (input) {
                    input.value = answer;
                    this.selectTextAnswer(answer);
                }
            }
        }
        
        console.log('Making AI suggestion visible');
        document.getElementById('ai-suggestion').style.display = 'block';
        console.log('AI suggestion element:', document.getElementById('ai-suggestion'));
    }

    getOptionLabel(value) {
        if (!this.currentQuestion.options) return value;
        const option = this.currentQuestion.options.find(opt => opt.value === value);
        return option ? option.label : value;
    }

    showResults(insuranceResponse) {
        this.hideQuestionScreen();
        this.showResultsScreen();
        
        // Show loading first
        document.getElementById('loading-results').style.display = 'block';
        
        // Simulate processing time
        setTimeout(() => {
            document.getElementById('loading-results').style.display = 'none';
            document.getElementById('results-content').style.display = 'block';
            
            this.displayInsuranceCards(insuranceResponse.insurance_cards);
            this.displayRecommendations(insuranceResponse.recommendations);
            
            document.getElementById('quotes-count').textContent = insuranceResponse.insurance_cards.length;
        }, 2000);
    }

    displayInsuranceCards(cards) {
        const container = document.getElementById('insurance-cards');
        
        if (!cards || cards.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">No insurance quotes available at this time.</div>';
            return;
        }

        const cardsHtml = cards.map(card => this.createInsuranceCardHtml(card)).join('');
        container.innerHTML = cardsHtml;
    }

    createInsuranceCardHtml(card) {
        const badges = [];
        if (card.recommended) badges.push('<span class="card-badge badge bg-success">Recommended</span>');
        if (card.best_value) badges.push('<span class="card-badge badge bg-warning text-dark">Best Value</span>');
        if (card.fastest_approval) badges.push('<span class="card-badge badge bg-info">Fastest Approval</span>');

        return `
            <div class="insurance-card ${card.recommended ? 'recommended' : ''} ${card.best_value ? 'best-value' : ''} fade-in">
                ${badges.join('')}
                <div class="row">
                    <div class="col-md-8">
                        <div class="company-name">${card.company_name}</div>
                        <div class="plan-name">${card.plan_name}</div>
                        
                        <div class="d-flex align-items-center gap-3 mb-3">
                            <div class="company-rating">
                                <i class="fas fa-star"></i>
                                <span>${card.company_rating}/5.0</span>
                            </div>
                            ${card.instant_approval ? '<div class="instant-approval"><i class="fas fa-bolt"></i> Instant Approval</div>' : ''}
                            <span class="value-score">Value Score: ${Math.round(card.value_score)}</span>
                        </div>

                        <ul class="benefits-list">
                            ${card.key_benefits.map(benefit => `<li>${benefit}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="col-md-4 text-md-end">
                        <div class="monthly-cost">${card.monthly_cost}</div>
                        <div class="coverage-amount">${card.coverage_amount} coverage</div>
                        
                        ${card.deductible ? `<div class="text-muted small">${card.deductible}</div>` : ''}
                        ${card.waiting_period ? `<div class="text-muted small">${card.waiting_period}</div>` : ''}
                        
                        <div class="mt-3">
                            <button class="btn btn-primary btn-sm me-2" onclick="app.selectPlan('${card.plan_id}')">
                                Select Plan
                            </button>
                            <button class="btn btn-outline-secondary btn-sm" onclick="app.showPlanDetails('${card.plan_id}')">
                                Details
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    displayRecommendations(recommendations) {
        const container = document.getElementById('recommendations-content');
        
        if (!recommendations || recommendations.length === 0) {
            container.innerHTML = '<p class="text-muted">No specific recommendations available.</p>';
            return;
        }

        const recommendationsHtml = recommendations.map(rec => this.createRecommendationHtml(rec)).join('');
        container.innerHTML = recommendationsHtml;
    }

    createRecommendationHtml(rec) {
        return `
            <div class="recommendation-item rank-${rec.rank} fade-in">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-1">
                        <span class="badge bg-primary me-2">#${rec.rank}</span>
                        Plan ID: ${rec.plan_id}
                    </h6>
                    <span class="confidence-score">${Math.round(rec.confidence_score)}% match</span>
                </div>
                
                <p class="mb-2">${rec.recommendation_summary}</p>
                
                <div class="pros-cons">
                    <div class="pros-list">
                        <h6 class="text-success small mb-2"><i class="fas fa-thumbs-up me-1"></i>Pros</h6>
                        <ul class="small">
                            ${rec.pros.map(pro => `<li>${pro}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="cons-list">
                        <h6 class="text-danger small mb-2"><i class="fas fa-thumbs-down me-1"></i>Considerations</h6>
                        <ul class="small">
                            ${rec.cons.map(con => `<li>${con}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    // Helper methods
    showHelpSection() {
        document.getElementById('help-section').style.display = 'block';
        document.getElementById('help-description').focus();
    }

    hideHelpSection() {
        document.getElementById('help-section').style.display = 'none';
        document.getElementById('help-description').value = '';
    }

    hideAISuggestion() {
        document.getElementById('ai-suggestion').style.display = 'none';
    }

    updateProgress() {
        const percentage = (this.currentProgress.current / this.currentProgress.total) * 100;
        document.getElementById('progress-bar').style.width = percentage + '%';
        document.getElementById('progress-text').textContent = 
            `${this.currentProgress.current} of ${this.currentProgress.total}`;
        document.getElementById('progress-section').style.display = 'block';
    }

    hideWelcomeScreen() {
        document.getElementById('welcome-screen').style.display = 'none';
    }

    showQuestionScreen() {
        document.getElementById('question-screen').style.display = 'block';
    }

    hideQuestionScreen() {
        document.getElementById('question-screen').style.display = 'none';
    }

    showResultsScreen() {
        document.getElementById('results-screen').style.display = 'block';
        document.getElementById('progress-section').style.display = 'none';
    }

    showLoading(message) {
        // Could implement a loading overlay here
        console.log('Loading:', message);
    }

    showError(message) {
        alert(message); // Simple error handling - could be improved with toast notifications
    }

    selectPlan(planId) {
        alert(`Plan ${planId} selected! This would typically redirect to the application process.`);
    }

    showPlanDetails(planId) {
        alert(`Showing details for plan ${planId}`);
    }

    startOver() {
        location.reload();
    }

    contactAgent() {
        alert('This would connect you with a licensed insurance agent.');
    }

    goBack() {
        // This would require implementing a history system
        alert('Back functionality not implemented in this demo.');
    }

    async handleProfileUpload(event) {
        const file = event.target.files[0];
        const statusDiv = document.getElementById('upload-status');
        const fileNameDiv = document.getElementById('file-name');
        
        if (!file) {
            fileNameDiv.innerHTML = '';
            statusDiv.innerHTML = '';
            return;
        }
        
        // Show file name and update button
        fileNameDiv.innerHTML = `<i class="fas fa-file me-1"></i> ${file.name}`;
        const chooseBtn = document.getElementById('choose-file-btn');
        chooseBtn.innerHTML = '<i class="fas fa-check me-1"></i> File Selected';
        chooseBtn.className = 'btn btn-success';
        
        try {
            statusDiv.innerHTML = '<div class="text-info"><i class="fas fa-spinner fa-spin me-1"></i> Processing file...</div>';
            
            const text = await file.text();
            console.log('File content:', text); // Debug log
            
            const profileData = JSON.parse(text);
            console.log('Parsed profile data:', profileData); // Debug log
            
            // Validate required fields
            const required = ['first_name', 'last_name', 'dob', 'gender', 'email'];
            const missing = required.filter(field => !profileData[field]);
            
            if (missing.length > 0) {
                throw new Error(`Missing required fields: ${missing.join(', ')}`);
            }
            
            statusDiv.innerHTML = '<div class="text-success"><i class="fas fa-check me-1"></i> Profile validated! Starting questionnaire...</div>';
            
            // Brief delay to show success message
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Start questionnaire with profile data
            await this.startQuestionnaireWithProfile(profileData);
            
        } catch (error) {
            console.error('Profile upload error:', error);
            statusDiv.innerHTML = `<div class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i> ${error.message}</div>`;
            fileNameDiv.innerHTML = `<i class="fas fa-file-excel me-1 text-danger"></i> ${file.name} (Error)`;
        }
    }

    async startQuestionnaireWithProfile(profileData) {
        try {
            this.showLoading('Starting with uploaded profile...');
            
            const response = await fetch('/api/start-session-with-profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(profileData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.currentProgress = data.progress;
            
            this.hideWelcomeScreen();
            this.showQuestionScreen();
            this.displayQuestion(data.current_question);
            this.updateProgress();

        } catch (error) {
            console.error('Error starting questionnaire with profile:', error);
            this.showError('Failed to start questionnaire with profile. Please try again or use manual entry.');
        }
    }
}

// Initialize the app when the page loads
const app = new QuestionnaireApp();

// Updated: 2025-08-10 19:27:49
