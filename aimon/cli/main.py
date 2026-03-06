"""
AIMON CLI - Command-line interface for the framework.

Usage:
    aimon scan "query"
    aimon monitor
    aimon status
    aimon analyze "url"

Commands:
    scan         Search for sources and analyze
    monitor      Continuous monitoring mode
    status       Show framework status
    analyze      Analyze specific URL
    alerts       Show alerts
    threats      Show detected threats
    report       Generate report
"""

import asyncio
import click
import json
from typing import Optional
import structlog
from pathlib import Path

from aimon.framework_api import AIMON
from aimon.sync import AIMONSync

logger = structlog.get_logger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    """AIMON - AI Monitoring Framework for leak detection."""
    ctx.ensure_object(dict)


@cli.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max sources to scan")
@click.option("--output", default=None, help="Output file (JSON)")
def scan(query: str, limit: int, output: Optional[str]):
    """Scan for sources matching query."""
    click.echo(f"[*] Scanning for: {query}")
    click.echo(f"[*] Using AIMON Framework")
    
    fw = AIMONSync()
    fw.initialize()
    
    try:
        # Search for sources
        click.echo(f"[+] Searching for sources...")
        sources = fw.search_sources(query)
        
        if not sources:
            click.echo("[-] No sources found")
            return
        
        click.echo(f"[+] Found {len(sources)} sources")
        
        # Display results
        for i, source in enumerate(sources[:limit], 1):
            click.echo(f"  {i}. {source.get('name', 'Unknown')} ({source.get('url', 'No URL')})")
        
        # Get threats
        threats = fw.get_threats()
        if threats:
            click.echo(f"\n[!] {len(threats)} threat(s) detected")
            for threat in threats:
                click.echo(f"  - {threat.get('threat_level', 'unknown').upper()}: " 
                          f"{threat.get('source_id', 'unknown')}")
        
        # Get alerts
        alerts = fw.get_alerts()
        if alerts:
            click.echo(f"\n[!] {len(alerts)} alert(s) generated")
        
        # Output JSON if requested
        if output:
            results = {
                "sources": sources,
                "threats": threats,
                "alerts": alerts,
            }
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            click.echo(f"\n[+] Results saved to {output}")
    
    finally:
        fw.shutdown()


@cli.command()
@click.option("--duration", default=300, help="Monitor duration (seconds)")
@click.option("--interval", default=30, help="Check interval (seconds)")
def monitor(duration: int, interval: int):
    """Monitor in continuous mode."""
    click.echo("[*] Starting AIMON monitoring mode")
    click.echo(f"[*] Duration: {duration}s, Interval: {interval}s")
    
    fw = AIMONSync()
    fw.initialize()
    
    try:
        import time
        start = time.time()
        
        while time.time() - start < duration:
            click.echo(f"[+] Status check at {time.time() - start:.0f}s")
            
            status = fw.get_status()
            
            # Show metrics
            metrics = status.get("metrics", {})
            click.echo(f"  Events: {metrics.get('events_emitted', 0)}")
            click.echo(f"  Pages crawled: {metrics.get('pages_crawled', 0)}")
            click.echo(f"  Threats: {metrics.get('threats_detected', 0)}")
            click.echo(f"  Alerts: {metrics.get('alerts_generated', 0)}")
            
            time.sleep(interval)
        
        click.echo("[+] Monitoring complete")
    
    finally:
        fw.shutdown()


@cli.command()
def status():
    """Show framework status."""
    fw = AIMONSync()
    fw.initialize()
    
    try:
        status_data = fw.get_status()
        
        click.echo("[*] AIMON Framework Status")
        click.echo(f"Initialized: {status_data.get('initialized', False)}")
        
        runtime = status_data.get("runtime", {})
        click.echo(f"Modules: {runtime.get('modules', 0)}")
        click.echo(f"Modules ready: {runtime.get('modules_ready', 0)}")
        
        metrics = status_data.get("metrics", {})
        click.echo(f"\nMetrics:")
        click.echo(f"  Events emitted: {metrics.get('events_emitted', 0)}")
        click.echo(f"  Pages crawled: {metrics.get('pages_crawled', 0)}")
        click.echo(f"  Threats detected: {metrics.get('threats_detected', 0)}")
        click.echo(f"  Alerts generated: {metrics.get('alerts_generated', 0)}")
        
        health = status_data.get("health", {})
        click.echo(f"\nHealth: {health.get('status', 'unknown')}")
    
    finally:
        fw.shutdown()


@cli.command()
def alerts():
    """Show active alerts."""
    fw = AIMONSync()
    fw.initialize()
    
    try:
        alerts_list = fw.get_alerts()
        
        if not alerts_list:
            click.echo("[-] No active alerts")
            return
        
        click.echo(f"[*] {len(alerts_list)} Active Alerts\n")
        
        for alert in alerts_list:
            click.echo(f"Alert: {alert.get('alert_id', 'unknown')}")
            click.echo(f"  Level: {alert.get('threat_level', 'unknown')}")
            click.echo(f"  Message: {alert.get('message', 'No message')}")
            click.echo(f"  Time: {alert.get('timestamp', 'unknown')}")
            click.echo()
    
    finally:
        fw.shutdown()


@cli.command()
def threats():
    """Show detected threats."""
    fw = AIMONSync()
    fw.initialize()
    
    try:
        threats_list = fw.get_threats()
        
        if not threats_list:
            click.echo("[-] No threats detected")
            return
        
        click.echo(f"[*] {len(threats_list)} Threats Detected\n")
        
        for threat in threats_list:
            click.echo(f"Threat: {threat.get('source_id', 'unknown')}")
            click.echo(f"  Level: {threat.get('threat_level', 'unknown')}")
            click.echo(f"  Score: {threat.get('threat_score', 0):.2f}")
            click.echo(f"  Assets: {len(threat.get('detected_assets', []))}")
            click.echo()
    
    finally:
        fw.shutdown()


if __name__ == "__main__":
    cli()
