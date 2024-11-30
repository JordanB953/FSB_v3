import sys
from pathlib import Path
import logging

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

import streamlit as st
import pandas as pd
from app.categorization.fuzzy_matcher import FuzzyMatcher
from app.categorization.ai_categorizer import AICategorizer
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from app.processors.pdf_processor import PDFProcessor
from app.statements import generate_financial_statements, cleanup_old_files

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Financial Statement Builder",
    page_icon="💰",
    layout="wide"
)

class FinancialStatementBuilderApp:
    # Add class constant for confidence threshold
    CONFIDENCE_THRESHOLD = 0.8  # Move this out of session state
    
    def __init__(self):
        """Initialize the Streamlit application."""
        self.setup_session_state()
        self.load_categorizers()
        
    def setup_session_state(self):
        """Initialize session state variables."""
        if 'transactions_df' not in st.session_state:
            st.session_state.transactions_df = None
        if 'categorized_df' not in st.session_state:
            st.session_state.categorized_df = None
        if 'company_name' not in st.session_state:
            st.session_state.company_name = None
        if 'company_industry' not in st.session_state:
            st.session_state.company_industry = None
        if 'statement_path' not in st.session_state:
            st.session_state.statement_path = None

    def get_company_info(self):
        """Get company information from user."""
        st.subheader("Company Information")
        
        # Company name input - show current value if exists
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.company_name if st.session_state.company_name else "",
            key="company_name_input"
        )
        
        # Industry selection - show current value if exists
        industries = [
            "Childcare",
            "Restaurant",
            "Retail",
            "Technology",
            "Healthcare",
            "Manufacturing",
            "Services",
            "Other"
        ]
        industry = st.selectbox(
            "Industry",
            industries,
            index=industries.index(st.session_state.company_industry) if st.session_state.company_industry in industries else 0,
            key="company_industry_select"
        )
        
        # Update session state if values change
        if company_name != st.session_state.company_name:
            st.session_state.company_name = company_name
        if industry != st.session_state.company_industry:
            st.session_state.company_industry = industry
            # Reload categorizers if industry changes
            self.load_categorizers()
        
        return bool(company_name and industry)

    def load_categorizers(self):
        """Initialize categorization engines."""
        try:
            # Only initialize FuzzyMatcher if industry is selected
            if st.session_state.company_industry:
                self.matcher = FuzzyMatcher(industry=st.session_state.company_industry)
            
                # Only initialize AI categorizer after industry is selected
                try:
                    app_dir = Path(__file__).resolve().parent.parent
                    dict_dir = app_dir / "dictionaries"
                    industry_dict = dict_dir / f"{st.session_state.company_industry.lower()}_categories.csv"
                    general_dict = dict_dir / "general_categories.csv"
                    
                    if industry_dict.exists() and general_dict.exists():
                        self.ai_categorizer = AICategorizer(
                            industry_dictionary_path=str(industry_dict),
                            general_dictionary_path=str(general_dict)
                        )
                    else:
                        logger.warning("Required dictionary files not found")
                        self.ai_categorizer = None
                except ValueError:
                    st.warning("AI API key not found. AI categorization will be disabled.")
                    self.ai_categorizer = None
            else:
                self.matcher = None
                self.ai_categorizer = None
                
        except Exception as e:
            st.error(f"Error loading categorizers: {str(e)}")

    def upload_transactions(self):
        """Handle transaction file upload selection."""
        st.subheader("Upload Bank and Credit Card Statements")
        
        # Store uploaded files in session state
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = []
        
        uploaded_file = st.file_uploader(
            "Must be native PDFs (downloaded PDFs, not scanned PDFs)",
            type=['pdf'],
            accept_multiple_files=True  # Allow multiple files
        )
        
        if uploaded_file:
            # Validate company info before accepting files
            if not st.session_state.company_name:
                st.error("Please enter company information before uploading files")
                return
            
            st.session_state.uploaded_files = uploaded_file
            st.success(f"Selected {len(uploaded_file)} files for processing")

    def process_and_categorize(self):
        """Process PDFs, categorize transactions, and generate statements."""
        if not st.session_state.uploaded_files:
            st.warning("Please select PDF files to process")
            return
        
        try:
            with st.spinner("Processing PDFs and categorizing transactions..."):
                # Initialize processors
                pdf_processor = PDFProcessor()
                all_transactions = pd.DataFrame()
                
                # Process each PDF
                for uploaded_file in st.session_state.uploaded_files:
                    logger.info(f"Processing PDF: {uploaded_file.name}")
                    
                    result = pdf_processor.process_pdf(
                        uploaded_file,
                        st.session_state.get('user_email', 'default_user@example.com'),
                        st.session_state.company_name
                    )
                    
                    if result and not result['transactions_df'].empty:
                        # Validate PDF processing output
                        self.validate_data(result['transactions_df'], 'pdf_processing')
                        all_transactions = pd.concat([
                            all_transactions, 
                            result['transactions_df']
                        ], ignore_index=True)
                
                if all_transactions.empty:
                    st.error("No transactions found in uploaded PDFs")
                    return
                
                logger.info(f"Total transactions found: {len(all_transactions)}")
                
                # Categorize transactions with fuzzy matching
                processed_transactions = []
                transactions_for_ai = []  # Track transactions needing AI categorization
                
                for _, transaction in all_transactions.iterrows():
                    processed = self.matcher.process_transaction(
                        transaction.to_dict(),
                        confidence_threshold=self.CONFIDENCE_THRESHOLD
                    )
                    
                    # Check if transaction needs AI categorization
                    if (processed['industry-dictionary-category-confidence-level'] < self.CONFIDENCE_THRESHOLD and
                        processed['general-dictionary-category-confidence-level'] < self.CONFIDENCE_THRESHOLD):
                        logger.debug(f"Transaction needs AI categorization: {processed['description']}")
                        # Convert Timestamp to string format before adding to AI processing list
                        ai_transaction = processed.copy()
                        if isinstance(ai_transaction['date'], pd.Timestamp):
                            ai_transaction['date'] = ai_transaction['date'].strftime('%Y-%m-%d')
                        transactions_for_ai.append(ai_transaction)
                    
                    processed_transactions.append(processed)
                
                # Use AI categorization if available and needed
                if self.ai_categorizer and transactions_for_ai:
                    logger.info(f"Processing {len(transactions_for_ai)} transactions with AI categorization")
                    try:
                        ai_results = self.ai_categorizer.process_transactions(transactions_for_ai)
                        
                        # Update processed transactions with AI results
                        if ai_results:  # Add check for successful AI results
                            for trans in processed_transactions:
                                matching_ai_result = next(
                                    (r for r in ai_results if r['short-description'] == trans['short-description']),
                                    None
                                )
                                if matching_ai_result:
                                    logger.debug(f"AI categorized: {trans['description']} -> {matching_ai_result['llm_category']}")
                                    trans['llm_category'] = matching_ai_result['llm_category']
                                    trans['llm_confidence'] = matching_ai_result['llm_confidence']
                        else:
                            logger.warning("AI categorization returned no results")
                    except Exception as e:
                        logger.error(f"Error during AI categorization: {str(e)}")
                        st.warning("AI categorization encountered an error. Proceeding with fuzzy match results only.")
                
                # Convert to DataFrame and validate
                categorized_df = pd.DataFrame(processed_transactions)
                self.validate_data(categorized_df, 'categorization')
                
                # Log categorization statistics
                total = len(categorized_df)
                fuzzy_matched = sum(1 for _, row in categorized_df.iterrows() 
                                  if row['industry-dictionary-category-confidence-level'] >= self.CONFIDENCE_THRESHOLD or 
                                     row['general-dictionary-category-confidence-level'] >= self.CONFIDENCE_THRESHOLD)
                ai_categorized = sum(1 for _, row in categorized_df.iterrows() 
                                   if pd.notna(row.get('llm_category')))
                
                logger.info(f"Categorization statistics:")
                logger.info(f"- Total transactions: {total}")
                logger.info(f"- Fuzzy matched: {fuzzy_matched}")
                logger.info(f"- AI categorized: {ai_categorized}")
                logger.info(f"- Uncategorized: {total - (fuzzy_matched + ai_categorized)}")
                
                # Prepare data for Excel generation
                excel_df = pd.DataFrame({
                    'Date': categorized_df['date'],
                    'Description': categorized_df['description'],
                    'Category': categorized_df.apply(
                        lambda x: (
                            x['industry-dictionary-category'] 
                            if x['industry-dictionary-category-confidence-level'] >= self.CONFIDENCE_THRESHOLD
                            else x['general-dictionary-category'] 
                            if x['general-dictionary-category-confidence-level'] >= self.CONFIDENCE_THRESHOLD
                            else x.get('llm_category', 'Uncategorized')
                        ),
                        axis=1
                    ),
                    'Amount': categorized_df['amount']
                })
                
                # Add End_of_Month column for financial statements
                excel_df['End_of_Month'] = excel_df['Date'].dt.to_period('M').dt.to_timestamp('M')
                
                # Validate Excel data
                self.validate_data(excel_df, 'excel_generation')
                
                # Store processed data
                st.session_state.transactions_df = all_transactions
                st.session_state.categorized_df = categorized_df
                
                # Generate financial statements
                output_path = generate_financial_statements(
                    transactions_df=excel_df,
                    company_name=st.session_state.company_name,
                    industry=st.session_state.company_industry.lower()
                )
                
                if output_path:
                    st.session_state.statement_path = output_path
                    st.success("Processing complete! Download your financial statements below.")
                    
                    # Show download button
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="Download Financial Statements",
                            data=file,
                            file_name=Path(output_path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.error("Error generating financial statements")
                    
                # Show debug information in expander
                with st.expander("Debug Information"):
                    st.write("Raw Transactions:")
                    st.dataframe(all_transactions)
                    
                    st.write("Categorization Results:")
                    st.dataframe(categorized_df)
                    
                    st.write("Excel Generation Data:")
                    st.dataframe(excel_df)
                
        except ValueError as e:
            st.error(f"Data validation error: {str(e)}")
            logger.error(f"Validation error: {str(e)}")
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
            logger.exception("Processing error")

    def validate_data(self, df: pd.DataFrame, stage: str):
        """Validate DataFrame at each stage."""
        if stage == 'pdf_processing':
            required = ['date', 'description', 'amount']
        elif stage == 'categorization':
            required = [
                'industry-dictionary-category',
                'industry-dictionary-category-confidence-level',
                'general-dictionary-category',
                'general-dictionary-category-confidence-level'
            ]
        elif stage == 'excel_generation':
            required = ['Date', 'Description', 'Category', 'Amount']
        else:
            raise ValueError(f"Unknown validation stage: {stage}")
        
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns for {stage}: {missing}")
        
        # Validate data types
        if stage in ['pdf_processing', 'excel_generation']:
            date_col = 'date' if stage == 'pdf_processing' else 'Date'
            amount_col = 'amount' if stage == 'pdf_processing' else 'Amount'
            
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                raise ValueError(f"{date_col} column must be datetime type")
            
            if not pd.api.types.is_numeric_dtype(df[amount_col]):
                raise ValueError(f"{amount_col} column must be numeric type")

    def show_results(self):
        """Display categorization results and visualizations."""
        if st.session_state.categorized_df is None:
            return
        
        df = st.session_state.categorized_df
        
        st.subheader("Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Transactions",
                len(df)
            )
            
        with col2:
            # Check if categorization has been done
            if 'category' in df.columns:
                categorized = df[df['category'].notna()].shape[0]
                categorized_pct = (categorized/len(df)*100) if len(df) > 0 else 0
            else:
                # Handle uncategorized data
                categorized = 0
                categorized_pct = 0
                
            st.metric(
                "Categorized",
                f"{categorized} ({categorized_pct:.1f}%)"
            )
            
        with col3:
            total_amount = df['amount'].sum()
            st.metric(
                "Total Amount",
                f"${total_amount:,.2f}"
            )
            
        with col4:
            # Check if confidence scores exist
            if 'confidence_score' in df.columns:
                avg_confidence = df[df['confidence_score'].notna()]['confidence_score'].mean()
                confidence_display = f"{avg_confidence:.1%}"
            else:
                confidence_display = "N/A"
                
            st.metric(
                "Avg Confidence",
                confidence_display
            )

        # Only show categorization visualizations if data is categorized
        if 'category' in df.columns:
            # Dictionary usage breakdown
            st.subheader("Categorization Sources")
            dict_usage = df['dictionary_used'].value_counts()
            fig = px.pie(
                values=dict_usage.values,
                names=dict_usage.index,
                title='Categories by Dictionary Source'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Visualizations
            tab1, tab2 = st.tabs(["Category Distribution", "Monthly Trends"])
            
            with tab1:
                # Category pie chart
                fig = px.pie(
                    df,
                    values='amount',
                    names='category',
                    title='Transactions by Category'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with tab2:
                # Monthly timeline
                monthly_data = df.groupby(
                    [df['date'].dt.to_period('M'), 'category']
                )['amount'].sum().reset_index()
                
                monthly_data['date'] = monthly_data['date'].astype(str)
                
                fig = px.line(
                    monthly_data,
                    x='date',
                    y='amount',
                    color='category',
                    title='Monthly Transactions by Category'
                )
                st.plotly_chart(fig, use_container_width=True)

            # Add financial statement generation button
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Generate Financial Statements"):
                    try:
                        # Prepare DataFrame with required columns
                        statements_df = df.copy()
                        statements_df['Date'] = pd.to_datetime(statements_df['date'])
                        statements_df['End_of_Month'] = pd.to_datetime(statements_df['date']).dt.to_period('M').dt.to_timestamp('M')
                        statements_df['Description'] = statements_df['description']
                        statements_df['Category'] = statements_df['category']
                        statements_df['Amount'] = statements_df['amount']
                        
                        # Generate statements
                        output_path = generate_financial_statements(
                            transactions_df=statements_df,
                            company_name=st.session_state.company_name,
                            industry=st.session_state.company_industry.lower()
                        )
                        
                        if output_path:
                            st.session_state.statement_path = output_path
                            st.success("Financial statements generated successfully!")
                        else:
                            st.error("Error generating financial statements")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        logger.exception("Statement generation error")

            # Add download button if statements were generated
            if st.session_state.statement_path:
                with col2:
                    with open(st.session_state.statement_path, "rb") as file:
                        st.download_button(
                            label="Download Financial Statements",
                            data=file,
                            file_name=Path(st.session_state.statement_path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

            # Detailed results table
            st.subheader("Categorized Transactions")
            st.dataframe(
                df.style.format({
                    'amount': '${:,.2f}',
                    'confidence_score': '{:.2%}'
                }),
                use_container_width=True
            )

    def run(self):
        """Main application loop."""
        st.title("Financial Statement Builder")
        
        # Always show company info section
        self.get_company_info()
        
        # Only proceed with rest of UI if company info is provided
        if st.session_state.company_name and st.session_state.company_industry:
            self.upload_transactions()
            
            # Add process button
            if st.session_state.uploaded_files:
                if st.button("Process & Generate Statements"):
                    if self.matcher is None:
                        st.error("Please select an industry before processing")
                    else:
                        self.process_and_categorize()
            
            # Show results if available
            if st.session_state.categorized_df is not None:
                self.show_results()
                
                # Add export option (moved from sidebar)
                st.download_button(
                    "Export Categorized Data",
                    data=st.session_state.categorized_df.to_csv(index=False),
                    file_name="categorized_transactions.csv",
                    mime="text/csv"
                )
            
            # Cleanup old files periodically
            cleanup_old_files()
        else:
            st.warning("Please enter company information to continue")

if __name__ == "__main__":
    app = FinancialStatementBuilderApp()
    app.run()