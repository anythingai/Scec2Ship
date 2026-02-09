describe('Onboarding Flow', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/onboarding/checklist', {
      body: [
        { id: 1, title: 'Task 1', description: 'Desc 1', completed: false },
        { id: 2, title: 'Task 2', description: 'Desc 2', completed: false }
      ]
    }).as('getChecklist');
    
    cy.intercept('POST', '/api/onboarding/task/status', {
      statusCode: 200,
      body: { success: true }
    }).as('updateStatus');

    cy.visit('/onboarding');
  });

  it('completes a task and updates progress', () => {
    cy.wait('@getChecklist');
    cy.get('.progress-bar').should('have.attr', 'style', 'width: 0%;');
    
    cy.get('input[type="checkbox"]').first().check();
    cy.wait('@updateStatus');
    
    cy.get('.task-item').first().should('have.class', 'completed');
    cy.get('.progress-bar').should('have.attr', 'style', 'width: 50%;');
  });
});
