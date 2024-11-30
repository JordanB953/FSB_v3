from openpyxl.chart import LineChart, Reference, BarChart
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import Marker
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Generates Excel charts for financial statements."""
    
    def __init__(self, worksheet, categories, section_rows):
        """
        Initialize chart generator.
        
        Args:
            worksheet: The Excel worksheet containing statement data
            categories: List of category dictionaries from CategoryMapper
            section_rows: Dictionary mapping sections to their row positions
        """
        self.ws = worksheet
        self.categories = categories
        self.section_rows = section_rows
        
        # Common chart settings
        self.chart_height = 15
        self.chart_width = 30
        
        # Get date range for categories
        self.last_col = self._get_last_column()
        self.cats = Reference(worksheet, min_col=3, min_row=1, max_col=self.last_col, max_row=1)
    
    def _get_last_column(self) -> int:
        """Get the last data column in the worksheet."""
        # Find last non-empty cell in header row
        for col in range(self.ws.max_column, 2, -1):
            if self.ws.cell(row=1, column=col).value is not None:
                return col
        return 3  # Minimum column number
    
    def create_revenue_chart(self) -> BarChart:
        """Create stacked bar chart showing revenue breakdown."""
        revenue_section = self.section_rows['Revenue']
        
        chart = BarChart()
        chart.type = "col"
        chart.grouping = "stacked"
        chart.title = "Revenues"
        chart.height = self.chart_height
        chart.width = self.chart_width
        
        chart.y_axis.majorGridlines = None
        chart.x_axis.majorGridlines = None
        chart.y_axis.number_format = '#,##0'
        
        # Use actual subcategory rows for data
        data = Reference(
            self.ws,
            min_col=3,
            min_row=min(revenue_section['subcategories']),
            max_col=self.last_col,
            max_row=max(revenue_section['subcategories'])
        )
        chart.add_data(data, titles_from_data=False)
        chart.set_categories(self.cats)
        
        # Set series names dynamically
        revenue_subcats = [cat['name'] for cat in self.categories 
                         if cat['parent'] == 'Revenue' and not cat['is_total']]
        for i, name in enumerate(revenue_subcats):
            chart.series[i].name = name
        
        return chart
    
    def create_cos_chart(self) -> BarChart:
        """Create stacked bar chart showing cost of sales vs revenue."""
        cos_section = self.section_rows['Cost of Sales']
        revenue_section = self.section_rows['Revenue']
        
        chart = BarChart()
        chart.type = "col"
        chart.grouping = "stacked"
        chart.title = "Cost of Sales vs Revenue"
        chart.height = self.chart_height
        chart.width = self.chart_width
        
        chart.y_axis.majorGridlines = None
        chart.x_axis.majorGridlines = None
        chart.y_axis.number_format = '#,##0'
        
        # Add cost of sales bars
        data = Reference(
            self.ws,
            min_col=3,
            min_row=min(cos_section['subcategories']),
            max_col=self.last_col,
            max_row=max(cos_section['subcategories'])
        )
        chart.add_data(data, titles_from_data=False)
        chart.set_categories(self.cats)
        
        # Set series names
        cos_subcats = [cat['name'] for cat in self.categories 
                      if cat['parent'] == 'Cost of Sales' and not cat['is_total']]
        for i, name in enumerate(cos_subcats):
            chart.series[i].name = name
        
        # Add revenue line
        revenue_line = LineChart()
        revenue_data = Reference(
            self.ws,
            min_col=3,
            min_row=revenue_section['end'],
            max_col=self.last_col,
            max_row=revenue_section['end']
        )
        revenue_line.add_data(revenue_data, titles_from_data=False)
        revenue_line.y_axis.axId = 200
        revenue_line.y_axis.crosses = "max"
        revenue_line.series[0].name = "Total Revenue"
        revenue_line.series[0].graphicalProperties.line.width = 2.25
        revenue_line.series[0].marker = Marker(symbol='circle')
        revenue_line.series[0].graphicalProperties.line.solidFill = "FF0000"
        
        chart += revenue_line
        return chart
    
    def create_opex_chart(self) -> BarChart:
        """Create stacked bar chart showing operating expenses vs gross income."""
        opex_section = self.section_rows['Operating Expenses']
        
        chart = BarChart()
        chart.type = "col"
        chart.grouping = "stacked"
        chart.title = "Operating Expenses vs Gross Income"
        chart.height = self.chart_height
        chart.width = self.chart_width
        
        chart.y_axis.majorGridlines = None
        chart.x_axis.majorGridlines = None
        chart.y_axis.number_format = '#,##0'
        
        # Add operating expenses bars
        data = Reference(
            self.ws,
            min_col=3,
            min_row=min(opex_section['subcategories']),
            max_col=self.last_col,
            max_row=max(opex_section['subcategories'])
        )
        chart.add_data(data, titles_from_data=False)
        chart.set_categories(self.cats)
        
        # Set series names
        opex_subcats = [cat['name'] for cat in self.categories 
                       if cat['parent'] == 'Operating Expenses' and not cat['is_total']]
        for i, name in enumerate(opex_subcats):
            chart.series[i].name = name
        
        # Add gross income line
        gross_line = LineChart()
        gross_data = Reference(
            self.ws,
            min_col=3,
            min_row=self.section_rows['Gross Income']['row'],
            max_col=self.last_col,
            max_row=self.section_rows['Gross Income']['row']
        )
        gross_line.add_data(gross_data, titles_from_data=False)
        gross_line.y_axis.axId = 200
        gross_line.y_axis.crosses = "max"
        gross_line.series[0].name = "Gross Income"
        gross_line.series[0].graphicalProperties.line.width = 2.25
        gross_line.series[0].marker = Marker(symbol='circle')
        gross_line.series[0].graphicalProperties.line.solidFill = "FF0000"
        
        chart += gross_line
        return chart
    
    def create_ebitda_chart(self) -> BarChart:
        """Create bar chart showing EBITDA trend."""
        chart = BarChart()
        chart.type = "col"
        chart.title = "EBITDA"
        chart.height = self.chart_height
        chart.width = self.chart_width
        
        chart.y_axis.majorGridlines = None
        chart.x_axis.majorGridlines = None
        chart.y_axis.number_format = '#,##0'
        
        data = Reference(
            self.ws,
            min_col=3,
            min_row=self.section_rows['EBITDA']['row'],
            max_col=self.last_col,
            max_row=self.section_rows['EBITDA']['row']
        )
        chart.add_data(data, titles_from_data=False)
        chart.set_categories(self.cats)
        
        return chart 