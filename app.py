import streamlit as st

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="LTE Drive Test Analyzer",
    page_icon="📊",
    layout="wide"
)

import pandas as pd
import numpy as np
import io
import os
import json
from modules.data_processor import process_tems_data, detect_file_format
from modules.analyzer import (
    analyze_coverage_problems,
    analyze_interference,
    analyze_handover_failures,
    analyze_throughput_bottlenecks,
    analyze_call_drops,
    analyze_cell_overloading,
    analyze_parameter_mismatches,
    analyze_qos_issues,
    analyze_rf_metrics,
    analyze_idle_connected_mode_failures
)
from modules.visualizer import (
    plot_map_data,
    plot_rsrp_distribution,
    plot_rsrq_distribution,
    plot_sinr_distribution,
    plot_handover_events,
    plot_throughput_analysis,
    plot_call_quality_metrics,
    create_summary_dashboard
)
from modules.database import (
    init_db, 
    save_drive_test, 
    save_analysis_report, 
    save_problem_areas,
    get_all_drive_tests,
    get_drive_test_by_id,
    get_reports_for_drive_test,
    get_problem_areas_for_drive_test,
    delete_drive_test
)

# Initialize the database
database_available = False
try:
    init_db()
    database_available = True
    st.sidebar.success("✅ Database connected successfully!")
except Exception as e:
    st.sidebar.error("❌ Database connection failed")
    st.sidebar.info("📝 The app will work without database functionality")
    database_available = False

# Define app title and description
st.title("LTE Network Drive Test Analyzer")
st.markdown("""
    Upload TEMS drive test logs to analyze LTE network performance and identify root causes of issues.
    This tool helps in analyzing coverage, interference, handovers, throughput, and call quality.
    
    Supported file formats:
    - CSV, Excel (XLSX/XLS), LOG, TXT: Full analysis supported
    - TRP: Basic detection supported (requires export to CSV/Excel from TEMS for full analysis)
""")

# Sidebar for uploads and settings
with st.sidebar:
    st.header("Data Input")
    uploaded_file = st.file_uploader("Upload TEMS Drive Test Log", 
                                    type=["csv", "log", "txt", "xlsx", "xls", "trp"],
                                    help="Upload TEMS drive test log files for analysis.")
    
    if uploaded_file is not None:
        file_format = detect_file_format(uploaded_file)
        if file_format == 'TEMS TRP':
            st.warning("""
            ⚠️ TRP file format detected. 
            
            This is a proprietary TEMS binary format that has limited support. 
            For best results, please export your TRP file to CSV or Excel format using TEMS software.
            
            Basic placeholder data will be shown for demonstration purposes.
            """)
        else:
            st.info(f"Detected format: {file_format}")
    
    st.header("Analysis Settings")
    
    analysis_types = st.multiselect(
        "Select Analysis Types",
        [
            "Coverage Problems",
            "Interference",
            "Handover Failures",
            "Throughput Bottlenecks",
            "Call Drops",
            "Cell Overloading",
            "Parameter Mismatches",
            "QoS Issues",
            "RF Metrics (RSRP, RSRQ, SINR)",
            "Idle/Connected Mode Failures"
        ],
        default=["Coverage Problems", "RF Metrics (RSRP, RSRQ, SINR)"]
    )
    
    # Thresholds for analysis
    st.subheader("Analysis Thresholds")
    rsrp_threshold = st.slider("RSRP Threshold (dBm)", -140, -70, -105)
    rsrq_threshold = st.slider("RSRQ Threshold (dB)", -20, 0, -15)
    sinr_threshold = st.slider("SINR Threshold (dB)", -10, 30, 5)
    
    # Generate report button
    generate_report = st.button("Generate Analysis Report")

# Main content area
if uploaded_file is None:
    # Create tabs for home and database
    tabs = st.tabs(["Home", "Database"])
    
    with tabs[0]:  # Home tab
        # Display info when no file is uploaded
        st.info("Please upload a TEMS drive test log file to begin analysis.")
        
        # Display example capabilities
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Key Features")
            st.markdown("""
            - **Coverage Analysis**: Identify areas with poor RSRP/RSRQ
            - **Interference Detection**: Find areas with high interference
            - **Handover Analysis**: Detect and analyze handover failures
            - **Throughput Analysis**: Identify throughput bottlenecks
            - **Call Quality**: Analyze call drops and quality issues
            """)
            
        with col2:
            st.subheader("Supported Analysis")
            st.markdown("""
            - Coverage Problems
            - Interference Issues
            - Handover Failures
            - Throughput Bottlenecks
            - Call Drops
            - Cell Overloading
            - Parameter Mismatches
            - QoS Issues
            - RF Metrics Analysis
            - Idle/Connected Mode Failures
            """)
    
    with tabs[1]:  # Database tab
        st.subheader("Drive Test Database")
        st.info("Upload a drive test file first to analyze and save it to the database.")
        
        # List all drive tests in the database
        st.subheader("Saved Drive Tests")
        
        try:
            drive_tests = get_all_drive_tests()
            
            if not drive_tests:
                st.info("No drive tests saved in the database yet.")
            else:
                # Convert to dataframe for display
                drive_tests_data = []
                for dt in drive_tests:
                    drive_tests_data.append({
                        "ID": dt.id,
                        "Filename": dt.filename,
                        "Format": dt.file_format,
                        "Upload Date": dt.upload_date.strftime("%Y-%m-%d %H:%M"),
                        "Records": dt.record_count,
                        "Start Time": dt.start_time.strftime("%Y-%m-%d %H:%M") if dt.start_time else "N/A",
                        "End Time": dt.end_time.strftime("%Y-%m-%d %H:%M") if dt.end_time else "N/A"
                    })
                
                # Display as dataframe
                st.dataframe(pd.DataFrame(drive_tests_data))
                
                # Select drive test for details
                selected_id = st.selectbox(
                    "Select Drive Test to View Details",
                    options=[dt["ID"] for dt in drive_tests_data],
                    format_func=lambda x: f"ID: {x} - {next((dt['Filename'] for dt in drive_tests_data if dt['ID'] == x), 'Unknown')}"
                )
                
                if selected_id:
                    # Get the selected drive test details
                    drive_test = get_drive_test_by_id(selected_id)
                    
                    if drive_test:
                        st.subheader(f"Drive Test Details: {drive_test.filename}")
                        
                        # Display basic info
                        detail_col1, detail_col2 = st.columns(2)
                        with detail_col1:
                            st.write(f"**ID:** {drive_test.id}")
                            st.write(f"**Filename:** {drive_test.filename}")
                            st.write(f"**Format:** {drive_test.file_format}")
                        
                        with detail_col2:
                            st.write(f"**Upload Date:** {drive_test.upload_date.strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"**Record Count:** {drive_test.record_count}")
                            st.write(f"**Time Range:** {drive_test.start_time.strftime('%Y-%m-%d %H:%M') if drive_test.start_time else 'N/A'} to {drive_test.end_time.strftime('%Y-%m-%d %H:%M') if drive_test.end_time else 'N/A'}")
                        
                        # Show metrics if available
                        if drive_test.metrics:
                            st.subheader("Test Metrics")
                            metrics = drive_test.metrics[0]  # Get the first (should be only) metrics object
                            
                            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                            with metric_col1:
                                if metrics.avg_rsrp is not None:
                                    st.metric("Avg RSRP (dBm)", f"{metrics.avg_rsrp:.2f}")
                            with metric_col2:
                                if metrics.avg_rsrq is not None:
                                    st.metric("Avg RSRQ (dB)", f"{metrics.avg_rsrq:.2f}")
                            with metric_col3:
                                if metrics.avg_sinr is not None:
                                    st.metric("Avg SINR (dB)", f"{metrics.avg_sinr:.2f}")
                            with metric_col4:
                                if metrics.avg_throughput_dl is not None:
                                    st.metric("Avg DL Throughput (Mbps)", f"{metrics.avg_throughput_dl/1000:.2f}")
                        
                        # Show analysis reports if available
                        reports = get_reports_for_drive_test(drive_test.id)
                        if reports:
                            st.subheader("Analysis Reports")
                            
                            for report in reports:
                                with st.expander(f"{report.analysis_type} - {report.report_date.strftime('%Y-%m-%d %H:%M')}"):
                                    st.write(f"**Analysis Type:** {report.analysis_type}")
                                    st.write(f"**Report Date:** {report.report_date.strftime('%Y-%m-%d %H:%M')}")
                                    
                                    # Display thresholds
                                    if report.threshold_values:
                                        st.write("**Thresholds:**")
                                        thresholds = json.loads(report.threshold_values)
                                        for key, value in thresholds.items():
                                            st.write(f"- {key}: {value}")
                                    
                                    # Display results
                                    if report.results:
                                        st.write("**Results:**")
                                        results = json.loads(report.results)
                                        for key, value in results.items():
                                            if not isinstance(value, dict) and not isinstance(value, list):
                                                st.write(f"- {key}: {value}")
                                    
                                    # Display root causes if available
                                    if report.root_causes:
                                        st.write("**Root Causes:**")
                                        for rc in report.root_causes:
                                            st.write(f"- **{rc.issue_type}** ({rc.severity}): {rc.description}")
                                            st.write(f"  Recommendation: {rc.recommendation}")
                        
                        # Show problem areas if available
                        problem_areas = get_problem_areas_for_drive_test(drive_test.id)
                        if problem_areas:
                            st.subheader("Problem Areas")
                            
                            # Group by problem type
                            problem_types = {}
                            for pa in problem_areas:
                                if pa.problem_type not in problem_types:
                                    problem_types[pa.problem_type] = []
                                problem_types[pa.problem_type].append(pa)
                            
                            for problem_type, areas in problem_types.items():
                                with st.expander(f"{problem_type} Problems ({len(areas)} areas)"):
                                    areas_data = []
                                    for area in areas:
                                        areas_data.append({
                                            "ID": area.id,
                                            "Latitude": area.latitude,
                                            "Longitude": area.longitude,
                                            "RSRP (dBm)": area.avg_rsrp,
                                            "RSRQ (dB)": area.avg_rsrq,
                                            "SINR (dB)": area.avg_sinr,
                                            "Cell ID": area.cell_id,
                                            "Description": area.description
                                        })
                                    st.dataframe(pd.DataFrame(areas_data))
                        
                        # Option to delete the drive test
                        if st.button(f"Delete Drive Test ID: {drive_test.id}"):
                            if delete_drive_test(drive_test.id):
                                st.success(f"Drive test '{drive_test.filename}' (ID: {drive_test.id}) deleted successfully!")
                                st.warning("Refresh the page to update the list.")
                            else:
                                st.error(f"Error deleting drive test ID: {drive_test.id}")
        
        except Exception as e:
            st.error(f"Error accessing database: {str(e)}")
            st.exception(e)
else:
    # Process the uploaded data
    try:
        with st.spinner("Processing drive test data..."):
            df = process_tems_data(uploaded_file)
            
            # Show basic statistics
            st.subheader("Data Overview")
            
            # Show special notification for TRP files
            file_format = detect_file_format(uploaded_file)
            if file_format == 'TEMS TRP':
                st.warning("""
                ⚠️ This is placeholder data for the TRP file. 
                
                TEMS TRP is a proprietary binary format that requires TEMS-specific libraries for full parsing.
                For accurate analysis, please export your data to CSV or Excel from the TEMS software.
                """)
            
            st.write(f"Total records: {len(df)}")
            st.write(f"Time range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
            
            # Display data sample
            with st.expander("View Data Sample"):
                st.dataframe(df.head(10))
            
            # Display basic metrics
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            with metrics_col1:
                if 'RSRP' in df.columns:
                    st.metric("Avg RSRP (dBm)", f"{df['RSRP'].mean():.2f}")
            with metrics_col2:
                if 'RSRQ' in df.columns:
                    st.metric("Avg RSRQ (dB)", f"{df['RSRQ'].mean():.2f}")
            with metrics_col3:
                if 'SINR' in df.columns:
                    st.metric("Avg SINR (dB)", f"{df['SINR'].mean():.2f}")
            with metrics_col4:
                if 'Throughput_DL' in df.columns:
                    st.metric("Avg DL Throughput (Mbps)", f"{df['Throughput_DL'].mean()/1000:.2f}")
            
            # Create tabs for different analysis
            tabs = st.tabs(["Map View", "RF Analysis", "Handover Analysis", 
                            "Throughput Analysis", "Call Quality", "Summary Report", "Database"])
            
            with tabs[0]:  # Map View
                st.subheader("Network Performance Map")
                st.caption("Geographical distribution of key network metrics")
                map_fig = plot_map_data(df)
                st.plotly_chart(map_fig, use_container_width=True)
            
            with tabs[1]:  # RF Analysis
                st.subheader("RF Metrics Analysis")
                
                # RF Metrics Analysis
                if "RF Metrics (RSRP, RSRQ, SINR)" in analysis_types:
                    rf_results = analyze_rf_metrics(df, rsrp_threshold, rsrq_threshold, sinr_threshold)
                    
                    rf_col1, rf_col2 = st.columns(2)
                    with rf_col1:
                        st.plotly_chart(plot_rsrp_distribution(df), use_container_width=True)
                        st.plotly_chart(plot_sinr_distribution(df), use_container_width=True)
                    
                    with rf_col2:
                        st.plotly_chart(plot_rsrq_distribution(df), use_container_width=True)
                        
                        # Display RF analysis results
                        st.subheader("RF Analysis Summary")
                        st.write(f"Coverage Issues: {rf_results['coverage_issues_pct']:.1f}% of samples")
                        st.write(f"Interference Issues: {rf_results['interference_issues_pct']:.1f}% of samples")
                        st.write(f"Good RF Conditions: {rf_results['good_rf_pct']:.1f}% of samples")
                
                # Coverage Problems Analysis
                if "Coverage Problems" in analysis_types:
                    st.subheader("Coverage Problems Analysis")
                    coverage_results = analyze_coverage_problems(df, rsrp_threshold, rsrq_threshold)
                    
                    # Display results
                    st.write(f"Coverage Issues: {coverage_results['coverage_issues_pct']:.1f}% of samples")
                    st.write(f"Areas with critical coverage problems: {coverage_results['critical_areas']} locations")
                    
                    # Display coverage problem areas
                    if len(coverage_results['problem_areas']) > 0:
                        st.subheader("Coverage Problem Areas")
                        st.dataframe(coverage_results['problem_areas'])
                
                # Interference Analysis
                if "Interference" in analysis_types:
                    st.subheader("Interference Analysis")
                    interference_results = analyze_interference(df, sinr_threshold)
                    
                    # Display results
                    st.write(f"Interference Issues: {interference_results['interference_issues_pct']:.1f}% of samples")
                    st.write(f"Areas with high interference: {interference_results['high_interference_areas']} locations")
                    
                    # Display interference problem areas
                    if len(interference_results['problem_areas']) > 0:
                        st.subheader("High Interference Areas")
                        st.dataframe(interference_results['problem_areas'])
            
            with tabs[2]:  # Handover Analysis
                st.subheader("Handover Analysis")
                
                if "Handover Failures" in analysis_types:
                    handover_results = analyze_handover_failures(df)
                    
                    # Display handover analysis
                    ho_col1, ho_col2 = st.columns(2)
                    
                    with ho_col1:
                        st.plotly_chart(plot_handover_events(df, handover_results), use_container_width=True)
                    
                    with ho_col2:
                        st.subheader("Handover Statistics")
                        st.write(f"Total Handovers: {handover_results['total_handovers']}")
                        st.write(f"Successful Handovers: {handover_results['successful_handovers']}")
                        st.write(f"Failed Handovers: {handover_results['failed_handovers']}")
                        st.write(f"Handover Success Rate: {handover_results['handover_success_rate']:.2f}%")
                        
                        if len(handover_results['failure_causes']) > 0:
                            st.subheader("Handover Failure Causes")
                            for cause, count in handover_results['failure_causes'].items():
                                st.write(f"{cause}: {count} occurrences")
            
            with tabs[3]:  # Throughput Analysis
                st.subheader("Throughput Analysis")
                
                if "Throughput Bottlenecks" in analysis_types:
                    throughput_results = analyze_throughput_bottlenecks(df)
                    
                    # Display throughput analysis
                    st.plotly_chart(plot_throughput_analysis(df, throughput_results), use_container_width=True)
                    
                    tp_col1, tp_col2 = st.columns(2)
                    
                    with tp_col1:
                        st.subheader("Throughput Statistics")
                        st.write(f"Average DL Throughput: {throughput_results['avg_dl_throughput']:.2f} Mbps")
                        st.write(f"Average UL Throughput: {throughput_results['avg_ul_throughput']:.2f} Mbps")
                        st.write(f"Peak DL Throughput: {throughput_results['peak_dl_throughput']:.2f} Mbps")
                        st.write(f"Peak UL Throughput: {throughput_results['peak_ul_throughput']:.2f} Mbps")
                    
                    with tp_col2:
                        st.subheader("Throughput Bottlenecks")
                        st.write(f"DL Bottleneck Areas: {throughput_results['dl_bottleneck_areas']} locations")
                        st.write(f"UL Bottleneck Areas: {throughput_results['ul_bottleneck_areas']} locations")
                        
                        if len(throughput_results['bottleneck_causes']) > 0:
                            st.subheader("Bottleneck Causes")
                            for cause, count in throughput_results['bottleneck_causes'].items():
                                st.write(f"{cause}: {count} occurrences")
            
            with tabs[4]:  # Call Quality
                st.subheader("Call Quality Analysis")
                
                call_analysis_types = [t for t in analysis_types if t in [
                    "Call Drops", "QoS Issues", "Cell Overloading"
                ]]
                
                if len(call_analysis_types) > 0:
                    # Analyze call drops
                    if "Call Drops" in analysis_types:
                        call_drop_results = analyze_call_drops(df)
                        
                        # Display call drop analysis
                        cd_col1, cd_col2 = st.columns(2)
                        
                        with cd_col1:
                            st.subheader("Call Drop Statistics")
                            st.write(f"Total Calls: {call_drop_results['total_calls']}")
                            st.write(f"Completed Calls: {call_drop_results['completed_calls']}")
                            st.write(f"Dropped Calls: {call_drop_results['dropped_calls']}")
                            st.write(f"Call Drop Rate: {call_drop_results['call_drop_rate']:.2f}%")
                        
                        with cd_col2:
                            if len(call_drop_results['drop_causes']) > 0:
                                st.subheader("Call Drop Causes")
                                for cause, count in call_drop_results['drop_causes'].items():
                                    st.write(f"{cause}: {count} occurrences")
                    
                    # Analyze QoS issues
                    if "QoS Issues" in analysis_types:
                        qos_results = analyze_qos_issues(df)
                        
                        st.subheader("QoS Analysis")
                        st.plotly_chart(plot_call_quality_metrics(df, qos_results), use_container_width=True)
                        
                        # Display QoS analysis
                        st.write(f"VoLTE MOS Issues: {qos_results['volte_mos_issues_pct']:.2f}% of calls")
                        st.write(f"Data Bearer QCI Issues: {qos_results['qci_issues_pct']:.2f}% of sessions")
                    
                    # Analyze cell overloading
                    if "Cell Overloading" in analysis_types:
                        overloading_results = analyze_cell_overloading(df)
                        
                        st.subheader("Cell Overloading Analysis")
                        st.write(f"Overloaded Cells: {len(overloading_results['overloaded_cells'])}")
                        
                        if len(overloading_results['overloaded_cells']) > 0:
                            st.dataframe(overloading_results['overloaded_cells'])
                else:
                    st.info("No call quality analysis types selected. Please select from the sidebar.")
            
            with tabs[5]:  # Summary Report
                st.subheader("Network Performance Summary Report")
                
                # Generate summary dashboard
                summary_fig = create_summary_dashboard(df, analysis_types)
                st.plotly_chart(summary_fig, use_container_width=True)
                
                # Root cause summary
                st.subheader("Root Cause Analysis Summary")
                
                root_causes = []
                
                # Add root causes based on selected analysis types
                if "Coverage Problems" in analysis_types:
                    coverage_results = analyze_coverage_problems(df, rsrp_threshold, rsrq_threshold)
                    if coverage_results['coverage_issues_pct'] > 10:
                        root_causes.append({
                            "Issue": "Coverage Problems",
                            "Severity": "High" if coverage_results['coverage_issues_pct'] > 25 else "Medium",
                            "Description": f"Poor signal coverage affecting {coverage_results['coverage_issues_pct']:.1f}% of the drive test area",
                            "Recommendation": "Review cell site placement and antenna configurations. Consider adding new sites in critical areas."
                        })
                
                if "Interference" in analysis_types:
                    interference_results = analyze_interference(df, sinr_threshold)
                    if interference_results['interference_issues_pct'] > 10:
                        root_causes.append({
                            "Issue": "Interference Issues",
                            "Severity": "High" if interference_results['interference_issues_pct'] > 25 else "Medium",
                            "Description": f"High interference affecting {interference_results['interference_issues_pct']:.1f}% of the drive test area",
                            "Recommendation": "Review PCI planning, adjust antenna tilts, and optimize frequency planning to reduce interference."
                        })
                
                if "Handover Failures" in analysis_types:
                    handover_results = analyze_handover_failures(df)
                    if handover_results['handover_success_rate'] < 95:
                        root_causes.append({
                            "Issue": "Handover Failures",
                            "Severity": "High" if handover_results['handover_success_rate'] < 90 else "Medium",
                            "Description": f"Handover failures with success rate of {handover_results['handover_success_rate']:.2f}%",
                            "Recommendation": "Review neighbor cell lists, optimize handover parameters, and check for missing neighbors."
                        })
                
                if "Throughput Bottlenecks" in analysis_types:
                    throughput_results = analyze_throughput_bottlenecks(df)
                    if throughput_results['dl_bottleneck_areas'] > 5 or throughput_results['ul_bottleneck_areas'] > 5:
                        root_causes.append({
                            "Issue": "Throughput Bottlenecks",
                            "Severity": "Medium",
                            "Description": f"Low throughput areas identified: {throughput_results['dl_bottleneck_areas']} DL and {throughput_results['ul_bottleneck_areas']} UL locations",
                            "Recommendation": "Check resource allocation, scheduling algorithms, and consider capacity expansions in affected cells."
                        })
                
                if "Call Drops" in analysis_types:
                    call_drop_results = analyze_call_drops(df)
                    if call_drop_results['call_drop_rate'] > 2:
                        root_causes.append({
                            "Issue": "Call Drops",
                            "Severity": "High" if call_drop_results['call_drop_rate'] > 5 else "Medium",
                            "Description": f"Call drop rate of {call_drop_results['call_drop_rate']:.2f}%",
                            "Recommendation": "Review RRC configuration, mobility parameters, and cell coverage overlaps to reduce drops."
                        })
                
                if root_causes:
                    st.dataframe(pd.DataFrame(root_causes))
                else:
                    st.info("No significant network issues detected based on the selected analysis types.")
                
                # Export report option
                st.download_button(
                    label="Download Summary Report",
                    data=pd.DataFrame(root_causes).to_csv(index=False) if root_causes else "No significant issues detected",
                    file_name="lte_drive_test_analysis_report.csv",
                    mime="text/csv"
                )
                
            with tabs[6]:  # Database
                st.subheader("Drive Test Database")
                st.write("Save and manage your drive test data and analysis results.")
                
                # Save current drive test to database
                save_col1, save_col2 = st.columns([2, 1])
                with save_col1:
                    # Save current test button
                    if database_available and st.button("Save Current Drive Test to Database"):
                        # Save the current drive test data
                        try:
                            drive_test = save_drive_test(
                                filename=uploaded_file.name,
                                file_format=file_format,
                                df=df
                            )
                            
                            # Also save any analysis that was done
                            if "RF Metrics (RSRP, RSRQ, SINR)" in analysis_types:
                                rf_results = analyze_rf_metrics(df, rsrp_threshold, rsrq_threshold, sinr_threshold)
                                thresholds = {
                                    "rsrp_threshold": rsrp_threshold,
                                    "rsrq_threshold": rsrq_threshold,
                                    "sinr_threshold": sinr_threshold
                                }
                                save_analysis_report(
                                    drive_test_id=drive_test.id,
                                    analysis_type="RF Metrics",
                                    thresholds=thresholds,
                                    results=rf_results
                                )
                            
                            # Save coverage analysis
                            if "Coverage Problems" in analysis_types:
                                coverage_results = analyze_coverage_problems(df, rsrp_threshold, rsrq_threshold)
                                thresholds = {
                                    "rsrp_threshold": rsrp_threshold,
                                    "rsrq_threshold": rsrq_threshold
                                }
                                save_analysis_report(
                                    drive_test_id=drive_test.id,
                                    analysis_type="Coverage Problems",
                                    thresholds=thresholds,
                                    results=coverage_results
                                )
                                
                                # Save problem areas
                                if len(coverage_results['problem_areas']) > 0:
                                    save_problem_areas(
                                        drive_test_id=drive_test.id,
                                        problem_type="Coverage",
                                        problem_areas_df=coverage_results['problem_areas']
                                    )
                            
                            st.success(f"Drive test '{uploaded_file.name}' saved to database successfully (ID: {drive_test.id})!")
                            
                        except Exception as e:
                            st.error(f"Error saving to database: {str(e)}")
                
                # List all drive tests in the database
                st.subheader("Saved Drive Tests")
                
                try:
                    drive_tests = get_all_drive_tests()
                    
                    if not drive_tests:
                        st.info("No drive tests saved in the database yet.")
                    else:
                        # Convert to dataframe for display
                        drive_tests_data = []
                        for dt in drive_tests:
                            drive_tests_data.append({
                                "ID": dt.id,
                                "Filename": dt.filename,
                                "Format": dt.file_format,
                                "Upload Date": dt.upload_date.strftime("%Y-%m-%d %H:%M"),
                                "Records": dt.record_count,
                                "Start Time": dt.start_time.strftime("%Y-%m-%d %H:%M") if dt.start_time else "N/A",
                                "End Time": dt.end_time.strftime("%Y-%m-%d %H:%M") if dt.end_time else "N/A"
                            })
                        
                        # Display as dataframe
                        st.dataframe(pd.DataFrame(drive_tests_data))
                        
                        # Select drive test for details
                        selected_id = st.selectbox(
                            "Select Drive Test to View Details",
                            options=[dt["ID"] for dt in drive_tests_data],
                            format_func=lambda x: f"ID: {x} - {next((dt['Filename'] for dt in drive_tests_data if dt['ID'] == x), 'Unknown')}"
                        )
                        
                        if selected_id:
                            # Get the selected drive test details
                            drive_test = get_drive_test_by_id(selected_id)
                            
                            if drive_test:
                                st.subheader(f"Drive Test Details: {drive_test.filename}")
                                
                                # Display basic info
                                detail_col1, detail_col2 = st.columns(2)
                                with detail_col1:
                                    st.write(f"**ID:** {drive_test.id}")
                                    st.write(f"**Filename:** {drive_test.filename}")
                                    st.write(f"**Format:** {drive_test.file_format}")
                                
                                with detail_col2:
                                    st.write(f"**Upload Date:** {drive_test.upload_date.strftime('%Y-%m-%d %H:%M')}")
                                    st.write(f"**Record Count:** {drive_test.record_count}")
                                    st.write(f"**Time Range:** {drive_test.start_time.strftime('%Y-%m-%d %H:%M') if drive_test.start_time else 'N/A'} to {drive_test.end_time.strftime('%Y-%m-%d %H:%M') if drive_test.end_time else 'N/A'}")
                                
                                # Show metrics if available
                                if drive_test.metrics:
                                    st.subheader("Test Metrics")
                                    metrics = drive_test.metrics[0]  # Get the first (should be only) metrics object
                                    
                                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                                    with metric_col1:
                                        if metrics.avg_rsrp is not None:
                                            st.metric("Avg RSRP (dBm)", f"{metrics.avg_rsrp:.2f}")
                                    with metric_col2:
                                        if metrics.avg_rsrq is not None:
                                            st.metric("Avg RSRQ (dB)", f"{metrics.avg_rsrq:.2f}")
                                    with metric_col3:
                                        if metrics.avg_sinr is not None:
                                            st.metric("Avg SINR (dB)", f"{metrics.avg_sinr:.2f}")
                                    with metric_col4:
                                        if metrics.avg_throughput_dl is not None:
                                            st.metric("Avg DL Throughput (Mbps)", f"{metrics.avg_throughput_dl/1000:.2f}")
                                
                                # Show analysis reports if available
                                reports = get_reports_for_drive_test(drive_test.id)
                                if reports:
                                    st.subheader("Analysis Reports")
                                    
                                    for report in reports:
                                        with st.expander(f"{report.analysis_type} - {report.report_date.strftime('%Y-%m-%d %H:%M')}"):
                                            st.write(f"**Analysis Type:** {report.analysis_type}")
                                            st.write(f"**Report Date:** {report.report_date.strftime('%Y-%m-%d %H:%M')}")
                                            
                                            # Display thresholds
                                            if report.threshold_values:
                                                st.write("**Thresholds:**")
                                                thresholds = json.loads(report.threshold_values)
                                                for key, value in thresholds.items():
                                                    st.write(f"- {key}: {value}")
                                            
                                            # Display results
                                            if report.results:
                                                st.write("**Results:**")
                                                results = json.loads(report.results)
                                                for key, value in results.items():
                                                    if not isinstance(value, dict) and not isinstance(value, list):
                                                        st.write(f"- {key}: {value}")
                                            
                                            # Display root causes if available
                                            if report.root_causes:
                                                st.write("**Root Causes:**")
                                                for rc in report.root_causes:
                                                    st.write(f"- **{rc.issue_type}** ({rc.severity}): {rc.description}")
                                                    st.write(f"  Recommendation: {rc.recommendation}")
                                
                                # Show problem areas if available
                                problem_areas = get_problem_areas_for_drive_test(drive_test.id)
                                if problem_areas:
                                    st.subheader("Problem Areas")
                                    
                                    # Group by problem type
                                    problem_types = {}
                                    for pa in problem_areas:
                                        if pa.problem_type not in problem_types:
                                            problem_types[pa.problem_type] = []
                                        problem_types[pa.problem_type].append(pa)
                                    
                                    for problem_type, areas in problem_types.items():
                                        with st.expander(f"{problem_type} Problems ({len(areas)} areas)"):
                                            areas_data = []
                                            for area in areas:
                                                areas_data.append({
                                                    "ID": area.id,
                                                    "Latitude": area.latitude,
                                                    "Longitude": area.longitude,
                                                    "RSRP (dBm)": area.avg_rsrp,
                                                    "RSRQ (dB)": area.avg_rsrq,
                                                    "SINR (dB)": area.avg_sinr,
                                                    "Cell ID": area.cell_id,
                                                    "Description": area.description
                                                })
                                            st.dataframe(pd.DataFrame(areas_data))
                                
                                # Option to delete the drive test
                                if st.button(f"Delete Drive Test ID: {drive_test.id}"):
                                    if delete_drive_test(drive_test.id):
                                        st.success(f"Drive test '{drive_test.filename}' (ID: {drive_test.id}) deleted successfully!")
                                        st.warning("Refresh the page to update the list.")
                                    else:
                                        st.error(f"Error deleting drive test ID: {drive_test.id}")
                
                except Exception as e:
                    st.error(f"Error accessing database: {str(e)}")
                    st.exception(e)
    
    except Exception as e:
        st.error(f"Error processing the data: {str(e)}")
        st.exception(e)
