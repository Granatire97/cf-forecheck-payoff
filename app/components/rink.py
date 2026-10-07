import rink_plotly.rink_plot as rink_plot
import plotly.graph_objects as go

def build_rink(df2):
    rink_fig = rink_plot.rink(setting='ozone', vertical=False)
    rink_fig.update_xaxes(range=[25, 101], constrain='domain')
    rink_fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
    rink_fig.add_trace(go.Heatmap(
        x=df2["cx"], y=df2["cy"], z=df2["rate"],
        customdata=df2["n"],
        colorscale="Blues", opacity=0.75,
        colorbar=dict(title='Shot Rate', tickformat=".0%"), 
        hovertemplate="%{z:.0%} led to a shot<br>%{customdata} wins<extra></extra>",
        texttemplate="%{z:.0%}",))
    return rink_fig